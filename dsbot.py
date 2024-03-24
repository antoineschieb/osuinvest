from datetime import datetime, timedelta
import functools
from math import ceil
import re
import time
import typing
import discord
from discord.ext import commands
import pandas as pd

from discord.ui import Button, View
from discord import ButtonStyle


from bank import add_pending_transaction, buy_stock, calc_price, find_transaction, remove_transaction_from_pending, check_for_alerts
from constants import FEED_CHANNEL_ID, DETAILS_CHANNEL_ID, ADMINS, id_name, name_id
from creds import discord_bot_token
from formulas import valuate
from routines import create_alert, create_new_investor
from templating import generate_profile_card, generate_stock_card
from visual import draw_table, plot_stock, print_market, print_profile, print_leaderboard, print_stock
from utils import get_investor_by_name, get_pilimg_from_url, get_portfolio, get_stock_by_id, pretty_time_delta, split_df, split_msg


intents = discord.Intents().all()
# intents = discord.Intents.none()
# intents.reactions = True
# intents.members = True
# intents.guilds = True
bot = commands.Bot(command_prefix='$', intents=intents, help_command=None)
# client = discord.Client(intents=intents)


async def run_blocking(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    """Runs a blocking function in a non-blocking way"""
    func = functools.partial(blocking_func, *args, **kwargs) # `run_in_executor` doesn't support kwargs, `functools.partial` does
    return await bot.loop.run_in_executor(None, func)

@bot.event
async def on_ready():
    print("Bot is ready")
    # await broadcast("Bot is ready")



@bot.command()
async def profile(ctx: commands.Context, *args):   
    def parse_args(args, ctx):
        args = list(args)
        if len(args)>1:
            raise RuntimeError
        elif len(args) <= 0:
            return ctx.message.author.name, ctx.message.author.display_avatar
        else:
            a = args[0]
            if a[0] == '<' and a[1] == '@' and a[-1] == '>':
                investor_id = a.replace("<","").replace(">","").replace("@","")
                u = bot.get_user(int(investor_id))               
                return u.name, u.display_avatar
            else:
                user = discord.utils.get(ctx.guild.members, name=a)
                if user is None:
                    raise ValueError(f"ERROR: Unknown user {a}")
                return a, user.display_avatar

    try:
        investor_name, display_avatar = parse_args(args, ctx)
    except ValueError as e:
        await ctx.reply(e)
        return

    avatar = get_pilimg_from_url(str(display_avatar))
    ret_str = await run_blocking(generate_profile_card, investor_name, avatar)
    
    if ret_str.startswith('ERROR:'):
        await ctx.reply(ret_str)
        return
    # Else, ret_str should be a file path
    await ctx.channel.send(file=discord.File(ret_str))


@bot.command()
async def market(ctx: commands.Context, *args):
    async def parse_args(args):
        args = list(args)
        n_hours=0
        n_days=0
        sortby='market_cap'
        if '-d' in args:
            idx = args.index('-d')
            n_days = int(args[idx+1])
        if '-h' in args:
            idx = args.index('-h')
            n_hours = int(args[idx+1])
        if '-sortby' in args:
            idx = args.index('-sortby')
            sortby = args[idx+1]
            if sortby not in ['market_cap','value','evolution','dividend']:
                raise NameError
        return n_hours, n_days, sortby
    try:
        n_hours, n_days, sortby = await parse_args(args)
    except:
        await ctx.reply(f'Could not parse arguments.\nUsage $market [-d days] [-h hours] [-sortby value | evolution | dividend]')
        return 
    
    df = await run_blocking(print_market, n_hours=n_hours, n_days=n_days, sortby=sortby)
    if isinstance(df,str) and df.startswith('ERROR:'):
        await ctx.reply(df)
        return 
    ret_files = await run_blocking(draw_table, df, f'plots/market', 28, 18)

    await ctx.send(content=f'Page (1/{len(ret_files)})', file=discord.File(ret_files[0]), view=PaginationView(ret_files))

@bot.command()
async def leaderboard(ctx: commands.Context):
    df = await run_blocking(print_leaderboard)
    ret_files = await run_blocking(draw_table, df, 'plots/lb', 20, min(12, len(df.index)),dpi=70)
    await ctx.send(content=f'Page (1/{len(ret_files)})', file=discord.File(ret_files[0]), view=PaginationView(ret_files))


@bot.command()
async def lb(ctx: commands.Context):
    await leaderboard(ctx)

@bot.command()
async def y(ctx: commands.Context):
    await yes(ctx)

@bot.command()
async def n(ctx: commands.Context):
    await no(ctx)

@bot.command()
async def stock(ctx: commands.Context, *args):
    def parse_args(args):
        args = list(args)
        #start by optional args -d and -h
        n_days = 0
        n_hours = 0
        if '-d' in args:
            idx = args.index('-d')
            n_days = int(args[idx+1])
            args.pop(idx+1)
            args.pop(idx)
        if '-h' in args:
            idx = args.index('-h')
            n_hours = int(args[idx+1])
            args.pop(idx+1)
            args.pop(idx)
        stock_name = ''
        for x in args:
            stock_name += x
            stock_name += ' '
        stock_name = stock_name.strip()
        stock_name = re.sub('"','',stock_name)
        stock_name = re.sub("'",'',stock_name)
        return stock_name.lower(), n_hours, n_days

    try:
        stock_name, n_hours, n_days = parse_args(args)
    except:
        await ctx.reply(f'Could not parse arguments.\nUsage: $stock <stock_name> [-d days] [-h hours]')
        return 

    ret_str = await run_blocking(generate_stock_card, stock_name, n_hours=n_hours, n_days=n_days)
    if ret_str.startswith('ERROR:'):
        await ctx.reply(ret_str)
        return
    # Else, ret_str should be a file path
    await ctx.channel.send(file=discord.File(ret_str))


async def broadcast(msg :str, channel_id=FEED_CHANNEL_ID):
    if msg.startswith("ERROR: "):
        return 
    channel = await bot.fetch_channel(channel_id)
    await channel.send(f'{datetime.now().strftime("%Y-%m-%d %H:%M:%S")} : {msg}')
    return


@bot.command()
async def buy(ctx: commands.Context, *args):
    def parse_args(args):
        args = list(args)
        quantity = round(float(args[-1]), 1)
        args.pop()
        stock_name = ''
        for x in args:
            stock_name += x
            stock_name += ' '
        stock_name = stock_name.strip()
        stock_name = re.sub('"','',stock_name)
        stock_name = re.sub("'",'',stock_name)
        return stock_name.lower(), quantity
    try:
        stock_name, quantity = parse_args(args)
    except:
        await ctx.reply(f'Could not parse arguments.\nUsage: $buy <stock> <quantity>')
        return 

    if quantity < 0.1:
        await ctx.reply(f'ERROR: quantity must be at least 0.1')
        return

    
    if quantity > 50:
        await ctx.reply(f'ERROR: You can only buy 50 shares maximum at once.\nIf you want to buy {quantity} shares, do it in multiple transactions.')
        return

    if stock_name.lower() not in name_id.keys():
        await ctx.reply(f'ERROR: Unknown stock {stock_name}')
        return
    stock_name = name_id[stock_name.lower()]
    
    # calc price
    buyer = get_investor_by_name(ctx.message.author.name)
    if isinstance(buyer, str) and buyer.startswith('ERROR:'):
        await ctx.reply(buyer)
        return
    stock = get_stock_by_id(stock_name)
    transaction_price = calc_price(buyer, stock, quantity)

    if isinstance(transaction_price, str) and transaction_price.startswith('ERROR:'):
        await ctx.reply(transaction_price)
        return

    # put in confirmations.csv
    await run_blocking(add_pending_transaction, ctx.message.author.name, stock_name, quantity)

    # ask for confirmation
    await ctx.reply(f'Do you really want to buy **{quantity} {id_name[stock_name]}** shares for **${abs(transaction_price)}**? ($y/$n)')



@bot.command()
async def sell(ctx: commands.Context, *args):
    def parse_args(args):
        args = list(args)
        if args[-1] == 'all':
            quantity = 'all'
        else:
            quantity = round(float(args[-1]),1)
        args.pop()
        stock_name = ''
        for x in args:
            stock_name += x
            stock_name += ' '
        stock_name = stock_name.strip()
        stock_name = re.sub('"','',stock_name)
        stock_name = re.sub("'",'',stock_name)
        return stock_name.lower(), quantity
    try:
        stock_name, quantity = parse_args(args)
    except:
        await ctx.reply(f'Could not parse arguments.\nUsage: $sell <stock> <quantity>')
        return 

    if stock_name.lower() not in name_id.keys():
        await ctx.reply(f'ERROR: Unknown stock {stock_name}')
        return
    
    stock_name = name_id[stock_name.lower()]

    if quantity == 'all':
        # check how many stocks there are. If it's more than 50, tell user all can't be sold
        pf = get_portfolio(ctx.message.author.name)
        if stock_name not in pf.index:
            await ctx.reply(f'ERROR: You do not own any {id_name[stock_name]} shares yet.')
            return
        all_stocks_owned = pf.loc[stock_name,'shares_owned']
        
        if all_stocks_owned > 50:
            await ctx.reply(f'ERROR: You are trying to sell {all_stocks_owned} shares, but you can only sell 50 shares maximum at once.')
            return
        else:
            quantity = all_stocks_owned

    if quantity < 0.1:
        await ctx.reply(f'ERROR: quantity must be at least 0.1')
        return
    
    if quantity > 50:
        await ctx.reply(f'ERROR: You can only sell 50 shares maximum at once.\nIf you want to sell {quantity} shares, do it in multiple transactions.')
        return

    # calc price
    buyer = get_investor_by_name(ctx.message.author.name)
    if isinstance(buyer, str) and buyer.startswith('ERROR:'):
        await ctx.reply(buyer)
        return
    stock = get_stock_by_id(stock_name)
    
    ret_object = calc_price(buyer, stock, -quantity, return_tax=True)
    if isinstance(ret_object, str) and ret_object.startswith('ERROR:'):
        await ctx.reply(ret_object)
        return
    else:
        transaction_price, tax_applied = ret_object

    # put in confirmations.csv
    await run_blocking(add_pending_transaction, ctx.message.author.name, stock_name, -quantity)

    # ask for confirmation
    await ctx.reply(f'[{round(100*tax_applied,2)}% of tax applied]\nDo you really want to sell **{quantity} {id_name[stock_name]}** shares for **${abs(transaction_price)}**? ($y/$n)')

@bot.command()
async def yes(ctx: commands.Context):
    stock_name, quantity = await run_blocking(find_transaction,ctx.message.author.name)
    if stock_name and quantity:
        ret_str = await run_blocking(buy_stock, ctx.message.author.name, stock_name, quantity)
        await ctx.reply(ret_str)
        await broadcast(ret_str)
    else:
        await ctx.reply(f'ERROR: No recent transaction found in the last 5 minutes')

@bot.command()
async def no(ctx: commands.Context):
    ret = await run_blocking(remove_transaction_from_pending, ctx.message.author.name)
    if ret:
        await ctx.reply(f'Transaction cancelled')
    else:
        await ctx.reply(f'ERROR: No recent transaction found in the last 5 minutes')


@bot.command()
async def register(ctx: commands.Context):
    season_start_date = datetime(year=2024, month=3, day=17, hour=19, minute=0, second=0)  #Sunday 7pm
    if datetime.now() < season_start_date:
        td = season_start_date - datetime.now()
        await ctx.reply(f"You can't register before season starts!\nSeason will start in {pretty_time_delta(td.total_seconds())}")
    else:
        ret_str = await run_blocking(create_new_investor, ctx.message.author.name, 10000)
        await ctx.reply(ret_str)
        await broadcast(ret_str)


class PaginationView(View):
    def __init__(self, pages):
        super().__init__()
        self.page = 0
        self.pages = pages

    @discord.ui.button(custom_id="prev2", label='Prev', emoji='◀')
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page > 0:
            self.page -= 1
        else:
            self.page = len(self.pages) - 1
        await interaction.response.edit_message(content=f'Page ({self.page+1}/{len(self.pages)})', attachments=[discord.File(self.pages[self.page])])

    @discord.ui.button(custom_id="next2", label='Next', emoji='▶')
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if self.page < len(self.pages) - 1:
            self.page += 1
        else:
            self.page = 0
        await interaction.response.edit_message(content=f'Page ({self.page+1}/{len(self.pages)})', attachments=[discord.File(self.pages[self.page])])



@bot.command()
async def pingmeif(ctx: commands.Context, *args):
    def parse_args(args):
        args = list(args)
        assert len(args) == 3
        
        if args[0].lower() not in name_id.keys():
            raise KeyError(f'ERROR: Unknown stock {args[0]}')
        stock_id = name_id[args[0].lower()]
        
        if args[1]=='>':
            is_greater_than = True
        if args[1]=='<':
            is_greater_than = False
        value = float(args[2])
        return stock_id, is_greater_than, value
    
    investor = ctx.message.author.id
    try:
        stock_id, is_greater_than, value = parse_args(args)
    except KeyError as e:
        await ctx.reply(e)
        return 
    except:
        await ctx.reply(f'ERROR: Could not parse arguments.\nUsage: `pingmeif stock < value` or `pingmeif stock > value`')
        return

    ret_str = await run_blocking(create_alert, investor, stock_id, is_greater_than, value)
    await ctx.reply(ret_str)


@bot.command()
async def balance(ctx: commands.Context, *args):
    def parse_args(args, ctx):
        args = list(args)
        if len(args)>1:
            raise ValueError(f"Could not parse arguments.\nUsage: `$balance [investor]`")
        elif len(args) <= 0:
            return ctx.message.author.name
        else:
            a = args[0]
            if a[0] == '<' and a[1] == '@' and a[-1] == '>':
                investor_id = a.replace("<","").replace(">","").replace("@","")
                u = bot.get_user(int(investor_id))               
                return u.name
            else:
                return a

    try:
        investor_name = parse_args(args, ctx)
    except ValueError as e:
        await ctx.reply(e)
        return

    ret_str = await run_blocking(print_profile, investor_name)
    message_bits = split_msg(ret_str)
    for x in message_bits:
        x = "```"+x+"```"
        await ctx.reply(x)


@bot.command()
async def help(ctx: commands.Context, *args):
    await ctx.reply(f"Read <#{DETAILS_CHANNEL_ID}>")


@bot.command()
async def adminsell(ctx: commands.Context, *args):
    """
    $adminsell <investor> <stock> <qty>
    """
    if ctx.message.author.name not in ADMINS:
        await ctx.reply('Do not use admin commands!')
        await ctx.message.author.timeout(timedelta(minutes=5))
        return
    
    def parse_args(args):
        args = list(args)
        investor = args[0]
        args.pop(0)

        if args[-1] == 'all':
            quantity = 'all'
        else:
            quantity = float(args[-1])  # Do not round the quantity for adminsell
        args.pop()

        stock_name = ''
        for x in args:
            stock_name += x
            stock_name += ' '
        stock_name = stock_name.strip()
        stock_name = re.sub('"','',stock_name)
        stock_name = re.sub("'",'',stock_name)
        return investor, stock_name.lower(), quantity
    try:
        investor, stock_name, quantity = parse_args(args)
    except:
        await ctx.reply(f'Could not parse arguments.\nUsage: $adminsell <investor> <stock> <quantity>')
        return
    
    if stock_name.lower() not in name_id.keys():
        await ctx.reply(f'ERROR: Unknown stock {stock_name}')
        return
    
    stock_name = name_id[stock_name.lower()]
    
    if quantity == 'all':
        # check how many stocks there are. If it's more than 50, tell user all can't be sold
        pf = get_portfolio(investor)
        if stock_name not in pf.index:
            await ctx.reply(f'ERROR: {investor} does not own any {id_name[stock_name]} shares yet.')
            return
        all_stocks_owned = pf.loc[stock_name,'shares_owned']
        
        if all_stocks_owned > 50:
            await ctx.reply(f'ERROR: You are trying to sell {all_stocks_owned} shares, but you can only sell 50 shares maximum at once.')
            return
        else:
            quantity = all_stocks_owned


    ret_str = await run_blocking(buy_stock, investor, stock_name, -quantity)
    await ctx.reply(ret_str)
    await broadcast(ret_str)
    return     


if __name__ == "__main__":
    bot.run(discord_bot_token)

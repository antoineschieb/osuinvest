from datetime import datetime, timedelta
import functools
import json
from math import ceil
import re
import time
import typing
import discord
from discord.ext import commands
import numpy as np
import pandas as pd

from discord.ui import Button, View
from discord import ButtonStyle


from bank import add_pending_transaction, buy_stock, calc_price, find_transaction, remove_transaction_from_pending, check_for_alerts
from constants import FEED_CHANNEL_ID, DETAILS_CHANNEL_ID, ADMINS, SEASON_ID
from creds import discord_bot_token
from formulas import valuate
from routines import create_alert, create_new_investor, update_zero_tax_preferences
from templating import generate_profile_card, generate_stock_card
from visual import draw_table, get_price_df, plot_stock, print_market, print_portfolio, print_profile, print_leaderboard, print_stock
from utils import ban_user, get_avatar_from_discord_cache, get_id_name, get_investor_by_name, get_name_id, get_pilimg_from_url, get_portfolio, get_stock_by_id, beautify_time_delta, split_df, split_msg, time_parser


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

        args, td = time_parser(args)

        if len(args) <= 0:
            return ctx.message.author.name, td
        else:
            a = args[0]
            if a[0] == '<' and a[1] == '@' and a[-1] == '>':
                investor_id = a.replace("<","").replace(">","").replace("@","")
                u = bot.get_user(int(investor_id))               
                return u.name, td              
            return a, td

    try:
        investor_name, td = parse_args(args, ctx)
    except Exception as e:
        if str(e).startswith('ERROR:'):
            await ctx.reply(e)
        else:
            await ctx.reply(f'Could not parse arguments.\nUsage $profile <investor_name> [-d days] [-h hours] [-ever]')
        return

    avatar = get_avatar_from_discord_cache(investor_name)
    ret_str = await run_blocking(generate_profile_card, investor_name, avatar, td)
    
    if ret_str.startswith('ERROR:'):
        await ctx.reply(ret_str)
        return
    # Else, ret_str should be a file path
    await ctx.channel.send(file=discord.File(ret_str))


@bot.command()
async def market(ctx: commands.Context, *args):
    async def parse_args(args):
        args = list(args)
        
        to_csv = False
        sortby='market_cap'
        
        args, td = time_parser(args)
        
        if '-csv' in args:
            idx = args.index('-csv')
            args.pop(idx)
            to_csv = True
        if '-sortby' in args:
            idx = args.index('-sortby')
            sortby = args[idx+1]
            if sortby not in ['market_cap','m','value','v','evolution','e','dividend','d']:
                raise NameError
        return td, sortby, to_csv
    try:
        td, sortby, to_csv = await parse_args(args)
    except Exception as e:
        if str(e).startswith('ERROR:'):
            await ctx.reply(e)
        else:
            await ctx.reply(f'Could not parse arguments.\nUsage $market [-d days] [-h hours] [-sortby value | evolution | dividend]')
        return 
    
    df = await run_blocking(print_market, td, sortby=sortby)
    if isinstance(df,str) and df.startswith('ERROR:'):
        await ctx.reply(df)
        return 
    
    if to_csv:
        df.to_csv("plots/market.csv")
        await ctx.send(file=discord.File("plots/market.csv"))
    else:
        ret_files = await run_blocking(draw_table, df, f'plots/market', 28, 18)
        await ctx.send(content=f'Page (1/{len(ret_files)})', file=discord.File(ret_files[0]), view=PaginationView(ret_files) if len(ret_files)>1 else None)


@bot.command()
async def portfolio(ctx: commands.Context, *args):
    def parse_args(args, ctx):
        args = list(args)

        args, td = time_parser(args)

        sortby='profit'
        if '-sortby' in args:
            idx = args.index('-sortby')
            sortby = args[idx+1]
            if sortby not in ['value','v','current_total_value','c','dividend','d','profit','p']: 
                raise NameError("-sortby argument must be one of [value (v), current_total_value (c), dividend (d), profit (p)]")
            args.pop(idx)
            args.pop(idx)
        
        if len(args) <= 0:
            return ctx.message.author.name, td, sortby
        else:
            a = args[0]
            if a[0] == '<' and a[1] == '@' and a[-1] == '>':
                investor_id = a.replace("<","").replace(">","").replace("@","")
                u = bot.get_user(int(investor_id))               
                return u.name, td, sortby
            else:
                return a, td, sortby

    try:
        investor_name, td, sortby = parse_args(args, ctx)
    except Exception as e:
        if str(e).startswith('ERROR:'):
            await ctx.reply(e)
        else:
            await ctx.reply(f'Could not parse arguments.\nUsage $pf [-d days] [-h hours] [-ever] [-sortby (v)alue | (c)urrent_total_value | (d)ividend | (p)rofit]')
        return 
    
    # Filter df to show only the investor's stocks
    result = await run_blocking(print_portfolio, investor_name, td, sortby=sortby)
    
    if isinstance(result, str) and result.startswith('ERROR:'):
        await ctx.reply(result)
        return
    
    ret_files = await run_blocking(draw_table, result, f'plots/portfolio_{investor_name}', 28, 18)

    await ctx.send(content=f'Page (1/{len(ret_files)})', file=discord.File(ret_files[0]), view=PaginationView(ret_files) if len(ret_files)>1 else None)


@bot.command()
async def leaderboard(ctx: commands.Context):
    df = await run_blocking(print_leaderboard)
    ret_files = await run_blocking(draw_table, df, 'plots/lb', 20, min(12, len(df.index)), dpi=70)
    await ctx.send(content=f'Page (1/{len(ret_files)})', file=discord.File(ret_files[0]), view=PaginationView(ret_files) if len(ret_files)>1 else None)


@bot.command()
async def lb(ctx: commands.Context):
    await leaderboard(ctx)

@bot.command()
async def pf(ctx: commands.Context, *args):
    await portfolio(ctx, *args)

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
        args, td = time_parser(args)
        to_csv = False
        if '-csv' in args:
            idx = args.index('-csv')
            args.pop(idx)
            to_csv = True
        
        stock_name = ''
        for x in args:
            stock_name += x
            stock_name += ' '
        stock_name = stock_name.strip()
        stock_name = re.sub('"','',stock_name)
        stock_name = re.sub("'",'',stock_name)
        return stock_name.lower(), td, to_csv

    try:
        stock_name, td, to_csv = parse_args(args)
    except Exception as e:
        if str(e).startswith('ERROR:'):
            await ctx.reply(e)
        else:
            await ctx.reply(f'Could not parse arguments.\nUsage $stock [-d days] [-h hours] [-ever]')
        return 

    if to_csv:
        df = await run_blocking(get_price_df, stock_name, td)
        df.to_csv(f"plots/{stock_name}.csv")
        await ctx.send(file=discord.File(f"plots/{stock_name}.csv"))        
    else:
        ret_str = await run_blocking(generate_stock_card, stock_name, td)
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
    with open(f"{SEASON_ID}/season_config.json") as json_file:
        cfg = json.load(json_file)
        season_end_date = datetime.strptime(cfg['season_end_date'],'%Y-%m-%d %H:%M:%S')
        
    if datetime.now() >= season_end_date:
        td = season_end_date - datetime.now()
        await ctx.reply(f"Season has ended {beautify_time_delta(abs(td.total_seconds()))} ago!")
        return
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
    except Exception as e:
        if str(e).startswith('ERROR:'):
            await ctx.reply(e)
        else:
            await ctx.reply(f'Could not parse arguments.\nUsage $buy <stock> <quantity>')
        return 

    if quantity < 0.1:
        await ctx.reply(f'ERROR: quantity must be at least 0.1')
        return

    
    if quantity > 50:
        await ctx.reply(f'ERROR: You can only buy 50 shares maximum at once.\nIf you want to buy {quantity} shares, do it in multiple transactions.')
        return

    name_id = get_name_id()
    id_name = get_id_name()
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
    with open(f"{SEASON_ID}/season_config.json") as json_file:
        cfg = json.load(json_file)
        season_end_date = datetime.strptime(cfg['season_end_date'],'%Y-%m-%d %H:%M:%S')
        
    if datetime.now() >= season_end_date:
        td = season_end_date - datetime.now()
        await ctx.reply(f"Season has ended {beautify_time_delta(abs(td.total_seconds()))} ago!")
        return
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
    except Exception as e:
        if str(e).startswith('ERROR:'):
            await ctx.reply(e)
        else:
            await ctx.reply(f'Could not parse arguments.\nUsage $sell <stock> <quantity | all>')
        return 

    id_name = get_id_name()
    name_id = get_name_id()
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
    with open(f"{SEASON_ID}/season_config.json") as json_file:
        cfg = json.load(json_file)
        season_start_date = datetime.strptime(cfg['season_start_date'],'%Y-%m-%d %H:%M:%S')
        season_end_date = datetime.strptime(cfg['season_end_date'],'%Y-%m-%d %H:%M:%S')
        
    if datetime.now() <= season_start_date:
        td = season_start_date - datetime.now()
        await ctx.reply(f"You can't register before season starts!\nSeason will start in {beautify_time_delta(td.total_seconds())}")
        return
    if datetime.now() >= season_end_date:
        td = season_end_date - datetime.now()
        await ctx.reply(f"Season has ended {beautify_time_delta(abs(td.total_seconds()))} ago!")
        return
    ret_str = await run_blocking(create_new_investor, ctx.message.author.name, ctx.message.author.id, 10000)
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
        name_id = get_name_id()
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
        investor = args.pop(0)

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
    
    id_name = get_id_name()
    name_id = get_name_id()
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


@bot.command()
async def pingmezerotax(ctx: commands.Context, *args):
    def parse_args(args, ctx):
        args = list(args)
        if len(args)!=1:
            raise ValueError(f"Could not parse arguments.\nUsage: `$pingmezerotax < ON | OFF >`")
        a = args[0].lower()
        if a not in ['on','off']:
            raise ValueError(f"Could not parse arguments.\nUsage: `$pingmezerotax < ON | OFF >`")
        return 1 if a=='on' else 0
    try:
        zero_tax_bool = parse_args(args, ctx)
    except ValueError as e:
        await ctx.reply(e)
        return
    
    ret = await run_blocking(update_zero_tax_preferences, ctx.message.author.name, zero_tax_bool)
    if ret.startswith('ERROR:'):
        await ctx.reply(ret)
        return
    await ctx.reply(f"You will {'' if zero_tax_bool else 'not '}be pinged when your stocks can be sold for 0.0% tax.")



@bot.command()
async def ban(ctx: commands.Context, *args):
    """
    $ban <investor>
    """
    if ctx.message.author.name not in ADMINS:
        await ctx.reply('Do not use admin commands!')
        await ctx.message.author.timeout(timedelta(minutes=5))
        return
    
    def parse_args(args):
        args = list(args)
        assert len(args)==1
        investor = args[0]
        return investor
    try:
        investor = parse_args(args)
    except:
        await ctx.reply(f'Could not parse arguments.\nUsage: $ban <investor>')
        return
    
    ret_str = await run_blocking(ban_user, investor)
    await ctx.reply(ret_str)

# @bot.command()
# async def retrieve_hist(ctx: commands.Context):
#     messages = ctx.channel.history(limit=1000)
#     with open("test.txt", "a", encoding="utf-8") as myfile:
#         async for m in messages:
#             if 'share(s)' in m.content:
#                 myfile.write(m.content + '\n')
#     print("done")
    

if __name__ == "__main__":
    bot.run(discord_bot_token)

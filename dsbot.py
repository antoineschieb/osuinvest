from datetime import datetime, timedelta
import functools
import re
import time
import typing
import discord
from discord.ext import commands
import pandas as pd
from bank import add_pending_transaction, buy_stock, calc_price, find_transaction, remove_transaction_from_pending
from constants import FEED_CHANNEL_ID, id_name, name_id

from creds import discord_bot_token
from formulas import valuate
from routines import create_new_investor
from visual import plot_stock, print_market, print_profile, print_leaderboard, print_stock
from utils import get_investor_by_name, get_stock_by_name, split_msg


intents = discord.Intents().all()
# intents = discord.Intents.none()
# intents.reactions = True
# intents.members = True
# intents.guilds = True
bot = commands.Bot(command_prefix='$', intents=intents)
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
    def parse_args(args):
        args = list(args)
        if len(args) <= 0:
            a = ctx.message.author.name
        elif len(args)>1:
            raise RuntimeError
        else:
            a = args[0]
            if a[0] == '<' and a[1] == '@' and a[-1] == '>':
                a = a.replace("<","")
                a = a.replace(">","")
                a = a.replace("@","")
                a = bot.get_user(int(a)).name
        return a
    investor_name = parse_args(args)
    ret_str = await run_blocking(print_profile, investor_name)
    ret_str = "```"+ret_str+"```"
    await ctx.send(ret_str)

@bot.command()
async def market(ctx: commands.Context, *args):
    def parse_args(args):
        args = list(args)
        n_hours=24
        n_days=0
        if '-d' in args:
            idx = args.index('-d')
            n_days = int(args[idx+1])
        if '-h' in args:
            idx = args.index('-h')
            n_hours = int(args[idx+1])
        if '-sortby' in args:
            idx = args.index('-sortby')
            sortby = args[idx+1]
            if sortby not in ['price','evolution','dividend']:
                ctx.reply(f'ERROR: -sortby value/evolution/dividend')
        return n_hours, n_days, sortby
    try:
        n_hours, n_days,sortby = parse_args(args)
    except:
        await ctx.reply(f'Could not parse arguments.')
        return 
    
    ret_str = await run_blocking(print_market, n_hours=n_hours, n_days=n_days, sortby=sortby)
    message_bits = await run_blocking(split_msg, ret_str)
    for x in message_bits:
        x = "```"+x+"```"
        await ctx.send(x)

@bot.command()
async def leaderboard(ctx: commands.Context):
    ret_str = await run_blocking(print_leaderboard)
    ret_str = "```"+ret_str+"```"
    await ctx.send(ret_str)

@bot.command()
async def lb(ctx: commands.Context):
    await leaderboard(ctx)

@bot.command()
async def stock(ctx: commands.Context, *args):
    def parse_args(args):
        args = list(args)
        #start by optional args -d and -n
        n_days = 0
        n_hours = 24
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

    stock_name, n_hours, n_days = parse_args(args)

    await run_blocking(plot_stock, stock_name, n_hours=n_hours, n_days=n_days)
    ret_str = await run_blocking(print_stock, stock_name)
    ret_str = "```"+ret_str+"```"
    await ctx.send(ret_str)
    await ctx.channel.send(file=discord.File(f'plots/{stock_name}.png'))


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
        quantity = float(args[-1])
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
    
    stock_name = name_id[stock_name.lower()]
    
    # calc price
    buyer = get_investor_by_name(ctx.message.author.name)
    stock = get_stock_by_name(stock_name)
    transaction_price = calc_price(buyer, stock, quantity)

    # put in confirmations.csv
    await run_blocking(add_pending_transaction, ctx.message.author.name, stock_name, quantity)

    # ask for confirmation
    await ctx.reply(f'Do you really want to buy {quantity} {id_name[stock_name]} shares for ${transaction_price}? ($yes/$no)')

    
    # ret_str = await run_blocking(buy_stock, ctx.message.author.name, stock_name, quantity)
    # await ctx.reply(ret_str)
    # await broadcast(ret_str)


@bot.command()
async def sell(ctx: commands.Context, *args):
    def parse_args(args):
        args = list(args)
        quantity = float(args[-1])
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

    stock_name = name_id[stock_name.lower()]

    # calc price
    buyer = get_investor_by_name(ctx.message.author.name)
    stock = get_stock_by_name(stock_name)
    transaction_price = calc_price(buyer, stock, -quantity)

    # put in confirmations.csv
    await run_blocking(add_pending_transaction, ctx.message.author.name, stock_name, -quantity)

    # ask for confirmation
    await ctx.reply(f'Do you really want to sell {quantity} {id_name[stock_name]} shares for ${transaction_price}? ($yes/$no)')

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
    ret_str = await run_blocking(create_new_investor, ctx.message.author.name, 10000)
    await ctx.reply(ret_str)
    await broadcast(ret_str)


if __name__ == "__main__":
    bot.run(discord_bot_token)

from datetime import datetime
import re
import time
import discord
from discord.ext import commands
from bank import buy_stock

from creds import discord_bot_token
from routines import create_new_investor
from visual import plot_stock, print_market, print_profile, print_leaderboard, print_stock
from utils import split_msg

intents = discord.Intents().all()
# intents = discord.Intents.none()
# intents.reactions = True
# intents.members = True
# intents.guilds = True
bot = commands.Bot(command_prefix='$', intents=intents)
# client = discord.Client(intents=intents)


# USER INTERFACE: (bot commands)
# - print_leaderboard (print all inv) -- OK
# - print_market (print all stocks) -- OK but split msg
# - print_profile(arg:str) (print 1 inv)  -- OK
# - print_stock(arg: str or int) + plot_stock(arg: int n_hours | int n_days) -- 

# - register()
# - buy(args:stock str, quantity float)
# - sell(args:stock str, quantity float)


# ADMIN INTERFACE:
# - pay_dividends()
# - update_renames(), optional

# TODO:
# - broadcast(message: str)


@bot.event
async def on_ready():
    print("Bot is ready")
    await broadcast("Bot is ready")

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
    ret_str = print_profile(investor_name)
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
        return n_hours, n_days
    
    n_hours, n_days = parse_args(args)
    ret_str = print_market(n_hours=n_hours, n_days=n_days)
    message_bits = split_msg(ret_str)
    for x in message_bits:
        x = "```"+x+"```"
        await ctx.send(x)

@bot.command()
async def leaderboard(ctx: commands.Context):
    ret_str = print_leaderboard()
    ret_str = "```"+ret_str+"```"
    await ctx.send(ret_str)

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
        return stock_name, n_hours, n_days
        
    stock_name, n_hours, n_days = parse_args(args)

    plot_stock([stock_name], n_hours=n_hours, n_days=n_days)
    ret_str = print_stock(stock_name)
    ret_str = "```"+ret_str+"```"
    await ctx.send(ret_str)
    
    await ctx.channel.send(file=discord.File('stock.png'))


async def broadcast(msg, channel_id=854465506428977156):
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
        return stock_name, quantity
    stock_name, quantity = parse_args(args)

    ret_str = await buy_stock(ctx.message.author.name, stock_name, quantity)
    await ctx.reply(ret_str)
    await broadcast(ret_str)
    

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
        return stock_name, quantity
    stock_name, quantity = parse_args(args)

    ret_str = await buy_stock(ctx.message.author.name, stock_name, -quantity)
    await ctx.reply(ret_str)
    await broadcast(ret_str)


@bot.command()
async def register(ctx: commands.Context):
    ret_str = await create_new_investor(ctx.message.author.name, 10000)
    await ctx.reply(ret_str)
    await broadcast(ret_str)


if __name__ == "__main__":
    bot.run(discord_bot_token)

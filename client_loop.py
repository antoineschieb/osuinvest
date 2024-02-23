from datetime import datetime
import discord
from bank import pay_all_dividends
from dsbot import broadcast
from creds import discord_bot_token
import asyncio
from discord.ext import commands, tasks
from prestige_hype import compute_prestige_and_hype, compute_prestige_and_hype_async
from routines import refresh_player_data_raw, update_stock_async

from utils import get_stock_by_name_async, split_msg

intents = discord.Intents().all()
bot = discord.Client(intents=intents)


@bot.event
async def on_ready():
    print("Client loop started.")
    update_static_stats.start()
    await asyncio.sleep(3600)
    pay_all_dividends_async.start()


@tasks.loop(seconds=300)
async def update_static_stats():
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Updating all player stats...")
    try:
        await refresh_player_data_raw()
        df = await compute_prestige_and_hype_async()
        for x in df.index:
            pp,p,h = df.loc[x,:]
            stock = await get_stock_by_name_async(x)
            stock.raw_skill = pp
            stock.trendiness = h
            stock.prestige = p
            await update_stock_async(stock)
    except Exception as e:
        print(datetime.now(), e)
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Done!")



@tasks.loop(hours=1)
async def pay_all_dividends_async():
    channel = await bot.fetch_channel(854465506428977156) 
    ret_str = await pay_all_dividends()
    message_bits = split_msg(ret_str)
    for x in message_bits:
        x = "```"+x+"```"
        await channel.send(x)


if __name__=='__main__':
    
    bot.run(discord_bot_token)
    
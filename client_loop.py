from datetime import datetime
import functools
import typing
import discord
from bank import pay_all_dividends
from constants import FEED_CHANNEL_ID
from dsbot import broadcast
from creds import discord_bot_token
import asyncio
from discord.ext import commands, tasks
from prestige_hype import compute_prestige_and_hype
from routines import refresh_player_data_raw, update_stock

from utils import get_stock_by_name, split_msg

intents = discord.Intents().all()
client = discord.Client(intents=intents)



async def run_blocking(blocking_func: typing.Callable, *args, **kwargs) -> typing.Any:
    """Runs a blocking function in a non-blocking way"""
    func = functools.partial(blocking_func, *args, **kwargs) # `run_in_executor` doesn't support kwargs, `functools.partial` does
    return await client.loop.run_in_executor(None, func)


@client.event
async def on_ready():
    print("Client loop started.")
    update_static_stats.start()
    minutes_to_wait = 60 - datetime.now().minute
    await asyncio.sleep(60 * minutes_to_wait)
    pay_all_dividends_async.start()


@tasks.loop(seconds=300)
async def update_static_stats():
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Updating all player stats...")
    try:
        await run_blocking(refresh_player_data_raw)
        df = await run_blocking(compute_prestige_and_hype)
        for x in df.index:
            pp,p,h = df.loc[x,:]
            stock = await run_blocking(get_stock_by_name, x)
            stock.raw_skill = pp
            stock.trendiness = h
            stock.prestige = p
            await run_blocking(update_stock, stock)
    except Exception as e:
        print(datetime.now(), e)
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Done!")



@tasks.loop(hours=1)
async def pay_all_dividends_async():
    channel = await client.fetch_channel(FEED_CHANNEL_ID) 
    ret_str = await run_blocking(pay_all_dividends)
    message_bits = split_msg(ret_str)
    for x in message_bits:
        x = "```"+x+"```"
        await channel.send(x)


if __name__=='__main__':
    
    client.run(discord_bot_token)
    
from datetime import datetime, time
import functools
import typing
import discord
import pandas as pd
from bank import check_for_alerts, pay_all_dividends
from constants import FEED_CHANNEL_ID, SEASON_ID
from creds import discord_bot_token
import asyncio
from discord.ext import commands, tasks
from formulas import valuate
from prestige_hype import compute_prestige_and_hype
from routines import create_new_stock, log_all_net_worth, refresh_player_data_raw, update_stock, update_name_id
from constants import name_id, id_name
from utils import calculate_remaining_time, get_stock_by_id, split_msg
from visual import print_investors_gains

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
    seconds = calculate_remaining_time(datetime.now().time(), time(hour=20))
    await asyncio.sleep(seconds)
    pay_all_dividends_async.start()


@tasks.loop(seconds=300)
async def update_static_stats():
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Updating all player stats...")
    # try:
    await run_blocking(refresh_player_data_raw)
    df = await run_blocking(compute_prestige_and_hype)
    df_updates = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv", index_col='update_id')
    df_updates_appendice = pd.DataFrame(columns=['update_id','stock_id','value','datetime'])
    df_updates_appendice = df_updates_appendice.set_index('update_id')

    for i,x in enumerate(df.index):
        pp,p,h = df.loc[x,:]
        stock = await run_blocking(get_stock_by_id, x)
        if stock is not None:
            stock.raw_skill = pp
            stock.trendiness = h
            stock.prestige = p

            df_updates_appendice.loc[len(df_updates)+i, :] = [stock.name, valuate(stock), datetime.now()]

            await run_blocking(update_stock, stock, log_price=False)   # we'll log all the prices once at the end
        else:
            print("Need to create new stock....")
            await run_blocking(create_new_stock, x, pp, h, p)
    # except Exception as e:
    #     print(datetime.now(), e)
    
    # update stock prices
    df_updates = pd.concat([df_updates, df_updates_appendice])
    df_updates.to_csv(f"{SEASON_ID}/stock_prices_history.csv", index='update_id')

    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Done!")
    
    # Now check for alerts
    ret_strs = await run_blocking(check_for_alerts)
    channel = await client.fetch_channel(FEED_CHANNEL_ID)
    for s in ret_strs:
        print(s)
        # s = "```"+s+"```"
        await channel.send(s)
    return 


@tasks.loop(hours=24)
async def pay_all_dividends_async():
    # Pay all dividends
    channel = await client.fetch_channel(FEED_CHANNEL_ID) 
    ret_str, ret_dict = await run_blocking(pay_all_dividends)
    message_bits = split_msg(ret_str)
    for x in message_bits:
        x = "```"+x+"```"
        await channel.send(x)

    # log all_net_worth
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Logging net worth..")
    await run_blocking(log_all_net_worth)

    # Print net gains since last day
    ret_str = await run_blocking(print_investors_gains, ret_dict)
    await channel.send ("```"+ ret_str +"```")

    # Check for renames
    await run_blocking(update_name_id, name_id, id_name)

client.run(discord_bot_token)
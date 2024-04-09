from datetime import datetime, time
import functools
import typing
import discord
import pandas as pd
import os
from bank import check_for_alerts, check_for_zero_tax_alerts, pay_all_dividends
from constants import ALERTS_CHANNEL_ID, FEED_CHANNEL_ID, GUILD_ID, SEASON_ID
from creds import discord_bot_token
import asyncio
from discord.ext import commands, tasks
from discord import Member, Guild
from formulas import valuate
from prestige_hype import compute_prestige_and_hype
from routines import create_new_stock, log_all_net_worth, log_all_net_worth_continuous, refresh_player_data_raw, update_stock, update_name_id
from utils import append_lines_to_csv, calculate_remaining_time, get_id_name, get_name_id, get_stock_by_id, liquidate, split_msg
from visual import get_richest_investor, print_investors_gains
from game_related import create_id_list
from utils import get_pilimg_from_url
from osuapi import api

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
    seconds = calculate_remaining_time(datetime.now().time(), time(hour=20, minute=0))
    await asyncio.sleep(seconds)
    pay_all_dividends_async.start()


@tasks.loop(seconds=300)
async def update_static_stats():
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Updating all player stats...")
    
    name_id = get_name_id()
    id_name = get_id_name()
    old_id_name = {k:v for k,v in id_name.items()}  # Copy before updating
    # Update name_id, liquidate stocks if needed
    stocks_to_liquidate, in_market_users = await run_blocking(update_name_id, name_id, id_name)
    ret_msgs = await run_blocking(liquidate, stocks_to_liquidate, old_id_name)
    if len(ret_msgs)>0:
        channel = await client.fetch_channel(FEED_CHANNEL_ID) 
        for m in ret_msgs:
            print(m)
            await channel.send(m)
    # Refresh all player data
    await run_blocking(refresh_player_data_raw, in_market_users)
    df = await run_blocking(compute_prestige_and_hype)
    df_updates = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv")
    df_updates_appendice = pd.DataFrame(columns=['stock_id','value','datetime'])
    for i,x in enumerate(df.index):
        if i>=5:
            break
        pp,p,h = df.loc[x,:]
        stock = await run_blocking(get_stock_by_id, x)
        if stock is not None:
            stock.raw_skill = pp
            stock.trendiness = h
            stock.prestige = p

            df_updates_appendice.loc[len(df_updates)+i, :] = [int(stock.name), valuate(stock), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]

            await run_blocking(update_stock, stock, log_price=False)   # we'll log all the prices once at the end
        else:
            await run_blocking(create_new_stock, x, pp, h, p)
            print(f"New stock **{id_name[x]}** has entered the market!")
            channel = await client.fetch_channel(FEED_CHANNEL_ID) 
            await channel.send(f"New stock **{id_name[x]}** has entered the market!")

    # update stock prices
    lines = [list(df_updates_appendice.loc[x]) for x in df_updates_appendice.index]
    append_lines_to_csv(f"{SEASON_ID}/stock_prices_history.csv", lines)
    
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Logging continuous net worth...")
    # log all_net_worth (continuous)
    await run_blocking(log_all_net_worth_continuous)

    channel = await client.fetch_channel(FEED_CHANNEL_ID)

    # Find richest investor
    elon, net_worth = await run_blocking(get_richest_investor)
    if elon is not None:
        guild = client.get_guild(GUILD_ID)
        user = discord.utils.get(guild.members, name=elon)
        if user is None:
            print(f"ERROR: Unknown user {elon}")    
        else:
            role = discord.utils.get(guild.roles, name="Elon Musk")
            if role not in user.roles:
                # First, remove current richest investor role
                for m in role.members:
                    await m.remove_roles(role, reason=f'Has been taken over by {elon}!')

                # Then, give role to the new richest investor
                await user.add_roles(role, reason='Added automatically for having highest net worth')      
                await channel.send(f'🤑 {elon} is now <@&{role.id}> with a Net Worth of ${net_worth}! 🤑')  

    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Checking for alerts...")
    alerts_channel = await client.fetch_channel(ALERTS_CHANNEL_ID)
    # Check for alerts
    ret_strs = await run_blocking(check_for_alerts)
    for s in ret_strs:
        print(s)
        # s = "```"+s+"```"
        await alerts_channel.send(s)

    # Check for zero tax alerts
    ret_strs = await run_blocking(check_for_zero_tax_alerts)
    for s in ret_strs:
        print(s)
        # s = "```"+s+"```"
        await alerts_channel.send(s)

    # update discord avatar cache
    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: avatar cache...")
    await run_blocking(update_cache_discord)

    print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Done!")
    
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
    ret_str, top_investor = await run_blocking(print_investors_gains, ret_dict)
    if top_investor is not None:
        message_bits = split_msg(ret_str)
        for x in message_bits:
            x = "```"+x+"```"
            await channel.send(x)

        # Give Trader of the day role
        guild = client.get_guild(GUILD_ID)
        user = discord.utils.get(guild.members, name=top_investor)
        if user is None:
            print(f"ERROR: Unknown user {top_investor}")    
        else:
            role = discord.utils.get(guild.roles, name="Trader of the day")

            if role not in user.roles:
                # Remove current top investor role
                for m in role.members:
                    await m.remove_roles(role, reason=f'Has been taken over by {top_investor}!')

                await user.add_roles(role, reason='Added automatically for best net gains today')        
            await channel.send(f'👏 {top_investor} is now the <@&{role.id}> ! 👏')


def update_cache_discord():
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    investors = df.index
    guild = client.get_guild(GUILD_ID)
    for investor in investors:
        user = discord.utils.get(guild.members, name=investor)
        if user is not None:
            im = get_pilimg_from_url(user.display_avatar)
            im.save(f'plots/discordavatar_{investor}.png')

client.run(discord_bot_token)
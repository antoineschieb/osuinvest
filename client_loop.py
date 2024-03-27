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
from constants import name_id, id_name
from utils import calculate_remaining_time, get_stock_by_id, split_msg
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
    seconds = calculate_remaining_time(datetime.now().time(), time(hour=20))
    await asyncio.sleep(seconds)
    pay_all_dividends_async.start()
    

@tasks.loop(seconds=300)
async def update_static_stats():
    try:
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Updating all player stats...")
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
        
        # update stock prices
        df_updates = pd.concat([df_updates, df_updates_appendice])
        if 'Unnamed: 0' in df_updates.columns:
            df_updates = df_updates.drop('Unnamed: 0', axis=1)
        # df_updates = df_updates.dropna(axis=0)
        df_updates['datetime'] = pd.to_datetime(df_updates['datetime'], format="ISO8601")
        df_updates = df_updates.sort_values(by="datetime")
        df_updates.to_csv(f"{SEASON_ID}/stock_prices_history.csv", index='update_id')

        # log all_net_worth (continuous)
        await run_blocking(log_all_net_worth_continuous)
        print(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}: Done!")

        channel = await client.fetch_channel(FEED_CHANNEL_ID)
        
        # Find richest investor
        elon, net_worth = await run_blocking(get_richest_investor)
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
        update_cache_discord()

    except Exception as e:
        print(e)
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

    # Check for renames
    await run_blocking(update_name_id, name_id, id_name)

def update_cache_discord():
    if not os.path.exists("cache_discord"):
        os.makedirs("cache_discord")
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    investors = df.index
    guild = client.get_guild(GUILD_ID)
    for investor in investors:
        user = discord.utils.get(guild.members, name=investor)
        if user is not None:
            im = get_pilimg_from_url(user.display_avatar)
            im.save(f"cache_discord/{investor}.png")
        
    print("Saved discord avatars in cache.")

client.run(discord_bot_token)
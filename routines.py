from datetime import datetime
import glob
import json
import pandas as pd
import os 

import constants
from importlib import reload
from formulas import get_net_worth, valuate
from game_related import all_user_info, top_i, api
from utils import append_lines_to_csv, append_one_line_to_csv, get_id_name, get_investor_uuid, get_portfolio, get_uuid_investor


def refresh_player_data_raw(in_market_users, verbose=False):
    cols = ['pp', 'hit_accuracy', 'play_count', 'play_time', 'replays_watched_by_others', 'maximum_combo', 'badges', 'follower_count', 'is_active', 'is_silenced', 'join_date', 'mapping_follower_count', 'scores_first_count', 'scores_recent_count', 'support_level', 'id', 'rank_peak', 'rank_current_to_worst', 'rank_current_to_mean', 'rank_current_to_highest_ever', 'activity','last_month_activity','topplay_activity']
    df_raw = pd.DataFrame(columns=cols)
    df_raw = df_raw.set_index('id')
    for u in in_market_users:
        d = all_user_info(u)
        df_raw.loc[u.id,:] = d
    df_raw.to_csv(f"{constants.SEASON_ID}/player_data_raw.csv", index='id')
    if verbose:
        print(f'Refreshed all stats for top50 players')
    return

def update_stock(stock: pd.Series, log_price=True):
    """
    This function updates all static and dynamic values that define a stock
    """
    # 1-update dynamic values
    df = pd.read_csv(f"{constants.SEASON_ID}/all_stocks_dynamic.csv", index_col='name')
    df.loc[stock.name,:] = stock
    df.to_csv(f"{constants.SEASON_ID}/all_stocks_dynamic.csv", index='name')

    # 2-update static values
    df = pd.read_csv(f"{constants.SEASON_ID}/all_stocks_static.csv", index_col='name')
    df.loc[stock.name,:] = stock
    df.to_csv(f"{constants.SEASON_ID}/all_stocks_static.csv", index='name')

    if log_price:
        # 3-log price update in stocks_prices_history
        line = [int(stock.name), valuate(stock), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        append_one_line_to_csv(f"{constants.SEASON_ID}/stock_prices_history.csv",line)
    return


def update_buyer(buyer: pd.Series):
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    df = df.astype({"cash_balance": float})
    df.loc[buyer.name,:] = buyer
    df.to_csv(f"{constants.SEASON_ID}/all_investors.csv", index='name')
    return 



def create_new_investor(name, discord_uuid, initial_balance):
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    if name in df.index:
        return f'ERROR: You are already registered'

    df.loc[name,:] = initial_balance, 0   # Initial balance (float), zero_tax_alerts (bool)
    df.to_csv(f"{constants.SEASON_ID}/all_investors.csv", index='name')

    # Load, edit and write jsons
    uuid_investor = get_uuid_investor()
    investor_uuid = get_investor_uuid()
    
    uuid_investor[discord_uuid] = name
    investor_uuid[name] = discord_uuid

    with open(f"{constants.SEASON_ID}/uuid_investor.json", "w") as fp:
        json.dump(uuid_investor , fp)
    with open(f"{constants.SEASON_ID}/investor_uuid.json", "w") as fp:
        json.dump(investor_uuid , fp) 

    return f'{name} has entered the market with ${initial_balance}!'


def create_new_stock(name, raw_skill,trendiness,prestige,total_shares=1000,sold_shares=0):

    df_s = pd.read_csv(f"{constants.SEASON_ID}/all_stocks_static.csv", index_col='name')
    df_s.loc[name,:] = [raw_skill,trendiness,prestige]
    df_s.to_csv(f"{constants.SEASON_ID}/all_stocks_static.csv", index='name')

    df_d = pd.read_csv(f"{constants.SEASON_ID}/all_stocks_dynamic.csv", index_col='name')
    df_d.loc[name,:] = [total_shares, sold_shares]
    df_d.to_csv(f"{constants.SEASON_ID}/all_stocks_dynamic.csv", index='name')

    # log initial stock price in stocks_prices_history
    d = {'name':name, 'raw_skill': raw_skill, 'trendiness':trendiness, 'prestige':prestige, 'total_shares':total_shares, 'sold_shares':sold_shares}
    stock_object = pd.Series(data=d)  # need to create it manually in case it's not yet found inside all_stocks.csv (async behavior)

    line = [name, valuate(stock_object, L=[]), datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    append_one_line_to_csv(f"{constants.SEASON_ID}/stock_prices_history.csv", line)
    return


def log_transaction(investor, stock_id, quantity, price):
    line = [investor, int(stock_id), quantity, price, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
    append_one_line_to_csv(f"{constants.SEASON_ID}/transactions_history.csv",line)
    return


def log_all_net_worth():
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    lines = []
    for inv in df.index:
        nw = get_net_worth(inv)
        line = [inv, nw, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        lines.append(line)
    append_lines_to_csv(f"{constants.SEASON_ID}/net_worth_history.csv",lines)
    return

def log_all_net_worth_continuous():
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    lines = []
    # For better optimization, read transac_history once and for all
    transac_hist = pd.read_csv(f"{constants.SEASON_ID}/transactions_history.csv")
    transac_hist = transac_hist.astype({"stock_id": int,"quantity":float})

    for inv in df.index:
        nw = get_net_worth(inv, transac_hist=transac_hist)
        line = [inv, nw, datetime.now().strftime('%Y-%m-%d %H:%M:%S')]
        lines.append(line)
    append_lines_to_csv(f"{constants.SEASON_ID}/net_worth_history_continuous.csv",lines)
    return


def create_alert(investor: str, stock_id: int, is_greater_than: bool, value: float):
    line = [investor, int(stock_id), is_greater_than, value]
    append_one_line_to_csv(f"{constants.SEASON_ID}/alerts.csv", line)
    id_name = get_id_name()
    return f'You will be pinged when {id_name[stock_id]} {">" if is_greater_than else "<"} {value}'


def update_name_id(name_id, id_name):
    """
    Updates names : id correspondences for the top N players, taking renames into account. 
    """

    old_id_name = {k:v for k,v in id_name.items()}  # Copy before updating

    with open(f"{constants.SEASON_ID}/season_config.json") as json_file:
        cfg = json.load(json_file)
        N_in = cfg['N_in']
        N_out = cfg['N_out']

    top_N_out = []
    in_market_users = []  # Store user objects in a list for later so we dont have to call osu API twice
    # Update all players from top N_in, no matter what
    for i in range(N_in):
        uuid = top_i(i, country='FR')
        top_N_out.append(uuid)
        u = api.user(uuid, mode='osu')
        in_market_users.append(u)
        current_username = u.username
        id_name[uuid] = current_username
        name_id[current_username.lower()] = uuid
        for n in u.previous_usernames:
            name_id[n.lower()] = uuid

    
    for i in range(N_in, N_out):
        uuid = top_i(i, country='FR')
        top_N_out.append(uuid)
        if uuid in id_name.keys():  # player is not bankrupt yet
            in_market_users.append(api.user(uuid, mode='osu'))

    # Check that every player in id_name is still within the top N_out. If not, liquidate
    stocks_to_liquidate = [k for k in id_name.keys() if k not in top_N_out]

    # Remove stocks from id_name
    for s in stocks_to_liquidate:
        del id_name[s]
    # Remove stocks from name_id
    name_id = {k:v for k,v in name_id.items() if v not in stocks_to_liquidate}

    with open(f"{constants.SEASON_ID}/name_id.json", "w") as fp:
        json.dump(name_id , fp)
    with open(f"{constants.SEASON_ID}/id_name.json", "w") as fp:
        json.dump(id_name , fp) 
    return stocks_to_liquidate, in_market_users


def update_zero_tax_preferences(investor, zero_tax_bool):
    # Step 1: update the bool in all_investors.csv
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    df.loc[investor,'zero_tax_alerts'] = zero_tax_bool
    df.to_csv(f"{constants.SEASON_ID}/all_investors.csv", index='name')

    # Step 2: Add or remove all alerts for investor's current stocks in zta.csv
    if zero_tax_bool == 0:
        # Remove all (open by hand)
        df_zta = pd.read_csv(f"{constants.SEASON_ID}/zero_tax_alerts.csv", index_col=['investor','stock'])
        df_zta['last_bought'] = pd.to_datetime(df_zta['last_bought'], format="ISO8601")
        df_zta = df_zta.drop(investor)
        df_zta.to_csv(f"{constants.SEASON_ID}/zero_tax_alerts.csv", index=['investor','stock'])
    
    elif zero_tax_bool == 1:
        # Add all (use existing update_zta function for the sake of clarity)
        pf = get_portfolio(investor)
        for stock_id in pf.index:
            last_bought = pf.loc[stock_id,'last_bought']
            update_zta(investor, stock_id, last_bought)
    return


def update_zta(investor, stock_id, last_bought):
    df = pd.read_csv(f"{constants.SEASON_ID}/zero_tax_alerts.csv", index_col=['investor','stock'])
    df['last_bought'] = pd.to_datetime(df['last_bought'], format="ISO8601")
    df.loc[(investor,stock_id),'last_bought'] = last_bought
    df.to_csv(f"{constants.SEASON_ID}/zero_tax_alerts.csv", index=['investor','stock'])
    return
from datetime import datetime
import glob
import json
import pandas as pd
import os 

import constants
from importlib import reload
from formulas import get_net_worth, valuate
from game_related import all_user_info, top_i, api
from utils import get_portfolio, get_stock_by_id


def refresh_player_data_raw(verbose=False):
    reload(constants)
    cols = ['pp', 'hit_accuracy', 'play_count', 'play_time', 'replays_watched_by_others', 'maximum_combo', 'badges', 'follower_count', 'is_active', 'is_silenced', 'join_date', 'mapping_follower_count', 'scores_first_count', 'scores_recent_count', 'support_level', 'id', 'rank_peak', 'rank_current_to_worst', 'rank_current_to_mean', 'rank_current_to_highest_ever', 'activity','last_month_activity','topplay_activity']
    df_raw = pd.DataFrame(columns=cols)
    df_raw = df_raw.set_index('id')
    for uuid in constants.id_name.keys():
        d = all_user_info(uuid)
        df_raw.loc[uuid,:] = d
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
        df_updates = pd.read_csv(f"{constants.SEASON_ID}/stock_prices_history.csv", index_col='update_id')
        df_updates.loc[len(df_updates),:] = [stock.name, valuate(stock), datetime.now()]
        df_updates.to_csv(f"{constants.SEASON_ID}/stock_prices_history.csv", index='update_id')
    return


def update_buyer(buyer: pd.Series):
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    df.loc[buyer.name,:] = buyer
    df.to_csv(f"{constants.SEASON_ID}/all_investors.csv", index='name')
    return 



def create_new_investor(name, initial_balance):
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    if name in df.index:
        return f'ERROR: You are already registered'

    df.loc[name,:] = initial_balance, 0   # Initial balance (float), zero_tax_alerts (bool)
    df.to_csv(f"{constants.SEASON_ID}/all_investors.csv", index='name')

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
    df_updates = pd.read_csv(f"{constants.SEASON_ID}/stock_prices_history.csv", index_col='update_id')
    df_updates.loc[len(df_updates),:] = [name, valuate(stock_object), datetime.now()]
    df_updates.to_csv(f"{constants.SEASON_ID}/stock_prices_history.csv", index='name')
    return


# Deprecated since season.py exists, just create a new season.
def reset_all_trades():
    df = pd.read_csv(f"{constants.SEASON_ID}/all_stocks_dynamic.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv(f"{constants.SEASON_ID}/all_stocks_dynamic.csv", index='name')

    df = pd.read_csv(f"{constants.SEASON_ID}/all_stocks_static.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv(f"{constants.SEASON_ID}/all_stocks_static.csv", index='name')

    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv(f"{constants.SEASON_ID}/all_investors.csv", index='name')

    df = pd.read_csv(f"{constants.SEASON_ID}/transactions_history.csv", index_col='transaction_id')
    df = df.iloc[0:0]
    df.to_csv(f"{constants.SEASON_ID}/transactions_history.csv", index='transaction_id')

    df = pd.read_csv(f"{constants.SEASON_ID}/stock_prices_history.csv", index_col='update_id')
    df = df.iloc[0:0]
    df.to_csv(f"{constants.SEASON_ID}/stock_prices_history.csv", index='update_id')

    return

def log_transaction(investor, stock_id, quantity):
    # Read column types properly
    history = pd.read_csv(f"{constants.SEASON_ID}/transactions_history.csv", index_col='transaction_id')
    history = history.astype({"stock_id": int})
    history['datetime'] = pd.to_datetime(history['datetime'], format="ISO8601")
    
    t_id = len(history)
    history.loc[t_id,:] = [investor, int(stock_id), quantity, datetime.now()]
    history.to_csv(f"{constants.SEASON_ID}/transactions_history.csv", index='transaction_id')
    return


def log_all_net_worth():
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    hist = pd.read_csv(f"{constants.SEASON_ID}/net_worth_history.csv", index_col="log_id")
    for inv in df.index:
        nw = get_net_worth(inv)
        hist.loc[len(hist),:] = inv, nw, datetime.now()
    hist.to_csv(f"{constants.SEASON_ID}/net_worth_history.csv", index="log_id")
    return


def log_all_net_worth_continuous():
    df = pd.read_csv(f"{constants.SEASON_ID}/all_investors.csv", index_col='name')
    hist = pd.read_csv(f"{constants.SEASON_ID}/net_worth_history_continuous.csv", index_col="log_id")
    for inv in df.index:
        nw = get_net_worth(inv)
        hist.loc[len(hist),:] = inv, nw, datetime.now()
    hist.to_csv(f"{constants.SEASON_ID}/net_worth_history_continuous.csv", index="log_id")
    return


def create_alert(investor: str, stock_id: int, is_greater_than: bool, value: float):
    df = pd.read_csv(f"{constants.SEASON_ID}/alerts.csv", index_col="alert_id")
    df = df.astype({"stock": int})
    df.loc[len(df.index),:]  = [investor, stock_id, is_greater_than, value]
    df.to_csv(f"{constants.SEASON_ID}/alerts.csv", index="alert_id")
    return f'You will be pinged when {constants.id_name[stock_id]} {">" if is_greater_than else "<"} {value}'


def update_name_id(name_id, id_name):
    """
    Updates names : id correspondences for the top N players, taking renames into account. 
    """
    N = len(id_name)
    for i in range(N):
        uuid = top_i(i, country='FR')
        u = api.user(uuid, mode='osu')
        current_username = u.username
        id_name[uuid] = current_username
        name_id[current_username.lower()] = uuid
        for n in u.previous_usernames:
            name_id[n.lower()] = uuid
    with open(f"{constants.SEASON_ID}/name_id.json", "w") as fp:
        json.dump(name_id , fp)
    with open(f"{constants.SEASON_ID}/id_name.json", "w") as fp:
        json.dump(id_name , fp) 
    return


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
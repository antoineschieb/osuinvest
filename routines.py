from datetime import datetime
import glob
import json
import pandas as pd
import os 

from constants import SEASON_ID, id_name, name_id
from formulas import get_net_worth, valuate
from game_related import all_user_info, top_i, api
from utils import get_stock_by_id


def refresh_player_data_raw(verbose=False, new_season_id=None):
    if new_season_id is not None:
        season_id = new_season_id
    else:
        season_id = SEASON_ID
    cols = ['pp', 'hit_accuracy', 'play_count', 'play_time', 'replays_watched_by_others', 'maximum_combo', 'badges', 'follower_count', 'is_active', 'is_silenced', 'join_date', 'mapping_follower_count', 'scores_first_count', 'scores_recent_count', 'support_level', 'id', 'rank_peak', 'rank_current_to_worst', 'rank_current_to_mean', 'rank_current_to_highest_ever', 'activity','last_month_activity','topplay_activity']
    df_raw = pd.DataFrame(columns=cols)
    df_raw = df_raw.set_index('id')
    for uuid in id_name.keys():
        d = all_user_info(uuid)
        df_raw.loc[uuid,:] = d
    df_raw.to_csv(f"{season_id}/player_data_raw.csv", index='id')
    if verbose:
        print(f'Refreshed all stats for top50 players')
    return

def update_stock(stock: pd.Series, log_price=True):
    """
    This function updates all static and dynamic values that define a stock, but doesn't update its ownership
    """
    # 1-update dynamic values
    df = pd.read_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index_col='name')
    df.loc[stock.name,:] = stock
    df.to_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index='name')

    # 2-update static values
    df = pd.read_csv(f"{SEASON_ID}/all_stocks_static.csv", index_col='name')
    df.loc[stock.name,:] = stock
    df.to_csv(f"{SEASON_ID}/all_stocks_static.csv", index='name')

    if log_price:
        # 3-log price update in stocks_prices_history
        df_updates = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv", index_col='update_id')
        df_updates.loc[len(df_updates),:] = [stock.name, valuate(stock), datetime.now()]
        df_updates.to_csv(f"{SEASON_ID}/stock_prices_history.csv", index='update_id')
    return


def update_buyer(buyer: pd.Series):
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    df.loc[buyer.name,:] = buyer
    df.to_csv(f"{SEASON_ID}/all_investors.csv", index='name')
    return 


def update_stock_ownership(buyer_name, stock_name, quantity):
    stock_name = int(stock_name)
    ownership_df = pd.read_csv(f'{SEASON_ID}/ownerships/{stock_name}.csv', index_col='investor_name')
    if buyer_name in ownership_df.index:
        ownership_df.loc[buyer_name,:] += quantity
    else:
        ownership_df.loc[buyer_name,:] = quantity
    
    # remove buyers where qty<=0
    ownership_df = ownership_df[ownership_df['shares_owned']>0]

    ownership_df.to_csv(f'{SEASON_ID}/ownerships/{stock_name}.csv', index='investor_name')
    return 


def update_buyer_portfolio(buyer_name, stock_name, quantity):
    buyer_portfolio = pd.read_csv(f'{SEASON_ID}/portfolios/{buyer_name}.csv', index_col='stock_name')
    if stock_name in buyer_portfolio.index:
        buyer_portfolio.loc[stock_name,:] += float(quantity)
    else:
        buyer_portfolio.loc[stock_name,:] = float(quantity)

    # remove stocks where qty<=0
    buyer_portfolio = buyer_portfolio[buyer_portfolio['shares_owned']>0]

    buyer_portfolio.to_csv(f'{SEASON_ID}/portfolios/{buyer_name}.csv', index='stock_name')
    return 


def create_new_investor(name, initial_balance):
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    if name in df.index:
        return f'ERROR: You are already registered'

    df.loc[name,:] = initial_balance
    df.to_csv(f"{SEASON_ID}/all_investors.csv", index='name')

    df = pd.DataFrame(columns=['stock_name','shares_owned'])
    df = df.set_index('stock_name')
    df.to_csv(f'{SEASON_ID}/portfolios/{name}.csv', index='stock_name')
    return f'{name} has entered the market with ${initial_balance}!'


def create_new_stock(name, raw_skill,trendiness,prestige,total_shares=1000,sold_shares=0, new_season_id=None):
    if new_season_id is not None:
        season_id = new_season_id
    else:
        season_id = SEASON_ID

    df_s = pd.read_csv(f"{season_id}/all_stocks_static.csv", index_col='name')
    df_s.loc[name,:] = [raw_skill,trendiness,prestige]
    df_s.to_csv(f"{season_id}/all_stocks_static.csv", index='name')

    df_d = pd.read_csv(f"{season_id}/all_stocks_dynamic.csv", index_col='name')
    df_d.loc[name,:] = [total_shares, sold_shares]
    df_d.to_csv(f"{season_id}/all_stocks_dynamic.csv", index='name')

    df = pd.DataFrame(columns=['investor_name','shares_owned'])
    df = df.set_index('investor_name')
    df.to_csv(f'{season_id}/ownerships/{name}.csv', index='stock_name')

    # log initial stock price in stocks_prices_history
    d = {'name':name, 'raw_skill': raw_skill, 'trendiness':trendiness, 'prestige':prestige, 'total_shares':total_shares, 'sold_shares':sold_shares}
    stock_object = pd.Series(data=d)  # need to create it manually in case it's not yet found inside all_stocks.csv (async behavior)
    df_updates = pd.read_csv(f"{season_id}/stock_prices_history.csv", index_col='update_id')
    df_updates.loc[len(df_updates),:] = [name, valuate(stock_object), datetime.now()]
    df_updates.to_csv(f"{season_id}/stock_prices_history.csv", index='name')
    return


def reset_all_trades():
    files = glob.glob(f'{SEASON_ID}/portfolios/*.csv')
    for f in files:
        os.remove(f)
    files = glob.glob(f'{SEASON_ID}/ownerships/*.csv')
    for f in files:
        os.remove(f)

    df = pd.read_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index='name')

    df = pd.read_csv(f"{SEASON_ID}/all_stocks_static.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv(f"{SEASON_ID}/all_stocks_static.csv", index='name')

    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv(f"{SEASON_ID}/all_investors.csv", index='name')

    df = pd.read_csv(f"{SEASON_ID}/transactions_history.csv", index_col='transaction_id')
    df = df.iloc[0:0]
    df.to_csv(f"{SEASON_ID}/transactions_history.csv", index='transaction_id')

    df = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv", index_col='update_id')
    df = df.iloc[0:0]
    df.to_csv(f"{SEASON_ID}/stock_prices_history.csv", index='update_id')

    return

def log_transaction(investor, stock_id, quantity):
    # Read column types properly
    history = pd.read_csv(f"{SEASON_ID}/transactions_history.csv", index_col='transaction_id')
    history = history.astype({"stock_id": int})
    history['datetime'] = pd.to_datetime(history['datetime'])
    
    t_id = len(history)
    history.loc[t_id,:] = [investor, int(stock_id), quantity, datetime.now()]
    history.to_csv(f"{SEASON_ID}/transactions_history.csv", index='transaction_id')
    return


def log_all_net_worth():
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    hist = pd.read_csv(f"{SEASON_ID}/net_worth_history.csv", index_col="log_id")
    for inv in df.index:
        nw = get_net_worth(inv)
        hist.loc[len(hist),:] = inv, nw, datetime.now()
    hist.to_csv(f"{SEASON_ID}/net_worth_history.csv", index="log_id")
    return

def create_alert(investor: str, stock_id: int, is_greater_than: bool, value: float):
    df = pd.read_csv(f"{SEASON_ID}/alerts.csv", index_col="alert_id")
    df = df.astype({"stock": int})
    df.loc[len(df.index),:]  = [investor, stock_id, is_greater_than, value]
    df.to_csv(f"{SEASON_ID}/alerts.csv", index="alert_id")
    return f'You will be pinged when {id_name[stock_id]} {">" if is_greater_than else "<"} {value}'


def update_name_id(name_id, id_name, N=52):
    """
    Updates names : id correspondences for the top N players, taking renames into account. 
    """
    for i in range(N):
        uuid = top_i(i, country='FR')
        u = api.user(uuid)
        current_username = u.username
        id_name[uuid] = current_username
        name_id[current_username.lower()] = uuid
        for n in u.previous_usernames:
            name_id[n.lower()] = uuid
    with open(f"{SEASON_ID}/name_id.json", "w") as fp:
        json.dump(name_id , fp)
    with open(f"{SEASON_ID}/id_name.json", "w") as fp:
        json.dump(id_name , fp) 
    return

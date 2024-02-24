from datetime import datetime
import glob
import pandas as pd
import os 

from constants import id_name, name_id
from formulas import valuate
from osuapi import all_user_info
from utils import get_stock_by_name


def refresh_player_data_raw(verbose=False):
    cols = ['pp', 'hit_accuracy', 'play_count', 'play_time', 'replays_watched_by_others', 'maximum_combo', 'badges', 'follower_count', 'is_active', 'is_silenced', 'join_date', 'mapping_follower_count', 'scores_first_count', 'scores_recent_count', 'support_level', 'id', 'rank_peak', 'rank_current_to_worst', 'rank_current_to_mean', 'rank_current_to_highest_ever', 'activity','last_month_activity','topplay_activity']
    df_raw = pd.DataFrame(columns=cols)
    df_raw = df_raw.set_index('id')
    for uuid in id_name.keys():
        d = all_user_info(uuid)
        df_raw.loc[uuid,:] = d
    df_raw.to_csv("player_data_raw.csv", index='id')
    if verbose:
        print(f'Refreshed all stats for top50 players')
    return

def update_stock(stock: pd.Series):
    """
    This function updates all static and dynamic values that define a stock, but doesn't update its ownership
    """
    # 1-update dynamic values
    df = pd.read_csv("all_stocks_dynamic.csv", index_col='name')
    df.loc[stock.name,:] = stock
    df.to_csv("all_stocks_dynamic.csv", index='name')

    # 2-update static values
    df = pd.read_csv("all_stocks_static.csv", index_col='name')
    df.loc[stock.name,:] = stock
    df.to_csv("all_stocks_static.csv", index='name')

    # 3-log price update in stocks_prices_history
    df_updates = pd.read_csv("stock_prices_history.csv", index_col='update_id')
    df_updates.loc[len(df_updates),:] = [stock.name, valuate(stock), datetime.now()]
    df_updates.to_csv("stock_prices_history.csv", index='name')
    return


def update_buyer(buyer: pd.Series):
    df = pd.read_csv("all_investors.csv", index_col='name')
    df.loc[buyer.name,:] = buyer
    df.to_csv("all_investors.csv", index='name')
    return 


def update_stock_ownership(buyer_name, stock_name, quantity):
    ownership_df = pd.read_csv(f'ownerships/{stock_name}.csv', index_col='investor_name')
    if buyer_name in ownership_df.index:
        ownership_df.loc[buyer_name,:] += quantity
    else:
        ownership_df.loc[buyer_name,:] = quantity
    
    # remove buyers where qty<=0
    ownership_df = ownership_df[ownership_df['shares_owned']>0]

    ownership_df.to_csv(f'ownerships/{stock_name}.csv', index='investor_name')
    return 


def update_buyer_portfolio(buyer_name, stock_name, quantity):
    buyer_portfolio = pd.read_csv(f'portfolios/{buyer_name}.csv', index_col='stock_name')
    if stock_name in buyer_portfolio.index:
        buyer_portfolio.loc[stock_name,:] += float(quantity)
    else:
        buyer_portfolio.loc[stock_name,:] = float(quantity)

    # remove stocks where qty<=0
    buyer_portfolio = buyer_portfolio[buyer_portfolio['shares_owned']>0]

    buyer_portfolio.to_csv(f'portfolios/{buyer_name}.csv', index='stock_name')
    return 


def create_new_investor(name, initial_balance):
    df = pd.read_csv("all_investors.csv", index_col='name')
    if name in df.index:
        return f'ERROR: You are already registered'

    df.loc[name,:] = initial_balance
    df.to_csv("all_investors.csv", index='name')

    df = pd.DataFrame(columns=['stock_name','shares_owned'])
    df = df.set_index('stock_name')
    df.to_csv(f'portfolios/{name}.csv', index='stock_name')
    return f'{name} has entered the market with ${initial_balance}!'


def create_new_stock(name, raw_skill,trendiness,prestige,total_shares,sold_shares=0):
    df_s = pd.read_csv("all_stocks_static.csv", index_col='name')
    df_s.loc[name,:] = [raw_skill,trendiness,prestige]
    df_s.to_csv("all_stocks_static.csv", index='name')

    df_d = pd.read_csv("all_stocks_dynamic.csv", index_col='name')
    df_d.loc[name,:] = [total_shares, sold_shares]
    df_d.to_csv("all_stocks_dynamic.csv", index='name')

    df = pd.DataFrame(columns=['investor_name','shares_owned'])
    df = df.set_index('investor_name')
    df.to_csv(f'ownerships/{name}.csv', index='stock_name')

    # log initial stock price in stocks_prices_history
    df_updates = pd.read_csv("stock_prices_history.csv", index_col='update_id')
    df_updates.loc[len(df_updates),:] = [name, valuate(get_stock_by_name(name)), datetime.now()]
    df_updates.to_csv("stock_prices_history.csv", index='name')

    return


def reset_all_trades():
    files = glob.glob('portfolios/*.csv')
    for f in files:
        os.remove(f)
    files = glob.glob('ownerships/*.csv')
    for f in files:
        os.remove(f)

    df = pd.read_csv("all_stocks_dynamic.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv("all_stocks_dynamic.csv", index='name')

    df = pd.read_csv("all_stocks_static.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv("all_stocks_static.csv", index='name')

    df = pd.read_csv("all_investors.csv", index_col='name')
    df = df.iloc[0:0]
    df.to_csv("all_investors.csv", index='name')

    df = pd.read_csv("transactions_history.csv", index_col='transaction_id')
    df = df.iloc[0:0]
    df.to_csv("transactions_history.csv", index='transaction_id')

    df = pd.read_csv("stock_prices_history.csv", index_col='update_id')
    df = df.iloc[0:0]
    df.to_csv("stock_prices_history.csv", index='update_id')

    return

def log_transaction(investor, stock_id, quantity):
    # Read column types properly
    history = pd.read_csv("transactions_history.csv", index_col='transaction_id')
    history = history.astype({"stock_id": int})
    history['datetime'] = pd.to_datetime(history['datetime'])
    
    t_id = len(history)
    history.loc[t_id,:] = [investor, int(stock_id), quantity, datetime.now()]
    history.to_csv("transactions_history.csv", index='transaction_id')
    return



from csv import writer
from datetime import date, datetime, timedelta
from io import BytesIO
import json
from math import ceil
from urllib.request import Request, urlopen
from PIL import Image
import pandas as pd
from constants import SEASON_ID

def get_stock_by_id(name: int) -> pd.Series:
    assert isinstance(name, int)
    df_s = pd.read_csv(f"{SEASON_ID}/all_stocks_static.csv", index_col='name')
    df_d = pd.read_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index_col='name')
    if name not in df_s.index or name not in df_d.index:
        return None
    x_s = df_s.loc[name,:]
    x_d = df_d.loc[name,:]
    ret = pd.concat([x_s, x_d])
    return ret


def get_investor_by_name(name: str) -> pd.Series:
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    df = df.astype({"cash_balance": float, "zero_tax_alerts": int})
    if name not in df.index:
        return f'ERROR: Unknown investor: {name}'
    x = df.loc[name,:]
    return x


def get_portfolio(investor: str, short=False) -> pd.DataFrame:
    transac_hist = pd.read_csv(f"{SEASON_ID}/transactions_history.csv")
    transac_hist = transac_hist.astype({"stock_id": int,"quantity":float})
    transac_hist['datetime'] = pd.to_datetime(transac_hist['datetime'], format="ISO8601")
    transac_hist = transac_hist[transac_hist['investor'] == investor]


    pf = pd.DataFrame(columns=['stock_name','shares_owned','last_bought','bought_for'])
    pf = pf.set_index('stock_name')
    for stock_ever_owned in transac_hist['stock_id'].unique():
        all_trades_on_stock = transac_hist[transac_hist['stock_id']==stock_ever_owned]

        # Shares owned
        shares_owned = sum(all_trades_on_stock['quantity'])

        if not short:
            # Last bought
            only_positive = all_trades_on_stock[all_trades_on_stock['quantity'] > 0]
            last_bought = max(only_positive['datetime'])
        
            # Bought for
            quantities = list(all_trades_on_stock['quantity'])
            datetimes = list(all_trades_on_stock['datetime'])
            prices = list(all_trades_on_stock['price'])
            trade_hist = list(zip(quantities, datetimes, prices))
            
            p = compute_price_bought_for(trade_hist)
        else:
            last_bought = 0
            p = 0

        # Write
        if shares_owned > 0:
            pf.loc[stock_ever_owned] = shares_owned, last_bought, p
    return pf


def get_ownership(stock_id: int) -> pd.DataFrame:
    stock_id = int(stock_id)
    transac_hist = pd.read_csv(f"{SEASON_ID}/transactions_history.csv")
    transac_hist = transac_hist.astype({"stock_id": int,"quantity":float})
    transac_hist = transac_hist[transac_hist['stock_id'] == stock_id]

    own = pd.DataFrame(columns=['investor_name','shares_owned'])
    own = own.set_index('investor_name')
    for inv in transac_hist['investor'].unique():
        all_trades_of_investor = transac_hist[transac_hist['investor']==inv]
        shares_owned = sum(all_trades_of_investor['quantity'])
        if shares_owned > 0:
            own.loc[inv] = shares_owned
    return own


def get_balance(investor_name: str) -> float:
    investor = get_investor_by_name(investor_name)
    return round(investor.cash_balance,2)


def get_stock_value_timedelta(stock_name, td: timedelta, history=None, history_time_filtered=None):
    # if history_time_filtered is not None, td will be ignored

    if isinstance(stock_name, str):
        name_id = get_name_id()
        stock_name = name_id[stock_name.lower()]
    
    if history is None and history_time_filtered is None:
        history = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv")
        history = history.astype({"stock_id": int})
        history['datetime'] = pd.to_datetime(history['datetime'], format="ISO8601")

    if history_time_filtered is None:
        d = datetime.now() - td
        history_time_filtered = history[history['datetime'] >= d]
    assert len(history_time_filtered) > 0

    history_name_time_filtered = history_time_filtered[(history_time_filtered['stock_id'] == stock_name)]
    if not len(history_name_time_filtered) > 0:
        print(f'INFO: {stock_name} has no history yet. Returning 0 as first value.')
        return 0
    # make sure it's sorted
    history_name_time_filtered = history_name_time_filtered.sort_values(by='datetime')
    return history_name_time_filtered.iloc[0,:].value


def split_msg(msg, max_len=1999):
    if len(msg) < max_len:
        return [msg]
    else:
        # find indices of '\n'
        indices = [i for i, x in enumerate(msg) if x == "\n" and i<=max_len]
        cut = indices[-1]
        return [msg[:cut+1], *split_msg(msg[cut+1:])]


def split_df(df: pd.DataFrame, rows_per_page: int):
    if len(df) <= rows_per_page:
        return [df]

    pages=ceil(len(df.index)/rows_per_page)
    # Save column types
    dtypes = df.dtypes
    # add blank rows at the end if the length of total df is not divisible by pages
    if len(df.index) < rows_per_page * pages:
        nb_blank_rows = rows_per_page * pages - len(df.index)
        for i in range(nb_blank_rows):
            df.loc[-i,:] = [0]*len(df.columns)   # Quick hack since uuids cannot be negative. draw_table will mark these rows as blank
    df = df.astype(dtype=dtypes)

    idx_start = 0
    list_of_dfs = []
    while idx_start < len(df.index):
        df_to_append = df[idx_start:min(idx_start+rows_per_page, len(df.index))]
        list_of_dfs.append(df_to_append)
        idx_start+=rows_per_page
    return list_of_dfs


def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)


def calculate_remaining_time(t_now, t_payout):
    dt_now = datetime.combine(date.today(), t_now)
    dt_payout = datetime.combine(date.today(), t_payout)
    dateTimeDifference = dt_payout - dt_now
    if dateTimeDifference >= timedelta():   # is diff pos or neg
        return dateTimeDifference.total_seconds()
    else:
        return (timedelta(hours=24) + dateTimeDifference).total_seconds()


def get_pilimg_from_url(url):
    req = Request(
        url=url, 
        headers={'User-Agent': 'Mozilla/5.0'})
    webpage = urlopen(req).read()
    pilimg = Image.open(BytesIO(webpage)).convert("RGBA")
    return pilimg

def beautify_time_delta(seconds, include_seconds=True):
    sign_string = '-' if seconds < 0 else ''
    seconds = abs(int(seconds))
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    
    
    if days > 0:
        ret_str = '%s%dd %dh %dm %ds' % (sign_string, days, hours, minutes, seconds)
    elif hours > 0:
        ret_str = '%s%dh %dm %ds' % (sign_string, hours, minutes, seconds)
    elif minutes > 0:
        ret_str = '%s%dm %ds' % (sign_string, minutes, seconds)
    else:
        ret_str = '%s%ds' % (sign_string, seconds)
    
    if not include_seconds:
        ret_str = ret_str.split( )[:2]
        ret_str = ' '.join(ret_str)
    return ret_str

# TODO: rewrite this nicely as df
def get_stack_from_trade_hist(trade_hist):
    stack = []  # will contain only positive values
    for qty,tme in trade_hist:  # chronological order
        if qty>0:
            # add layer to stack
            stack.append([qty,tme])
        else:
            # "scrape off" layers from top to bottom
            qty_left = abs(qty)
            while qty_left > 0:
                top_layer_qty = stack[-1][0]
                if qty_left > top_layer_qty:  # remove this layer and decrease qty
                    qty_left -= top_layer_qty
                    del stack[-1]
                    
                else:  #modify value of top_layer
                    new_qty = top_layer_qty - qty_left
                    stack[-1][0] = new_qty
                    break   # break because we are done scraping
    return stack

def compute_price_bought_for(trade_hist):
    trade_hist_short = [x[0:2] for x in trade_hist]
    stack = get_stack_from_trade_hist(trade_hist_short)
    p = 0
    all_timestamps = [x[1] for x in trade_hist]
    for layer in stack:
        i = all_timestamps.index(layer[1])
        inferred_stock_value = trade_hist[i][2] / trade_hist[i][0]
        price_of_this_layer = inferred_stock_value * layer[0]
        p+=price_of_this_layer
    return p


def get_sold_shares(stock_id):
    if isinstance(stock_id, int):
        own = get_ownership(stock_id)
    elif isinstance(stock_id, pd.Series):
        own = get_ownership(stock_id.name)
    return sum(own['shares_owned'])


def ban_user(investor_name):
    # 1-all_investors
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv")
    df = df.drop(df[df['name'] == investor_name].index)
    df.to_csv(f"{SEASON_ID}/all_investors.csv", index=None)
    
    # 2- all jsons    
    # banned_uuid = investor_uuid[investor_name]
    # del investor_uuid[investor_name]
    # del uuid_investor[banned_uuid]
    # Export the new jsons
    # TODO: take care of this too

    # 3- all csvs (loop)
    files = ["alerts","confirmations","net_worth_history_continuous","net_worth_history","transactions_history","zero_tax_alerts"]
    for f in files:
        df = pd.read_csv(f"{SEASON_ID}/{f}.csv")
        df = df.drop(df[df['investor'] == investor_name].index)
        df.to_csv(f"{SEASON_ID}/{f}.csv", index=None)

    # 4 - recompute all stocks sold_shares
    df = pd.read_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index_col='name')
    df['sold_shares'] = df.apply(lambda x:get_sold_shares(x.name), axis=1)
    df.to_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index='name')

    return f"Successfully removed {investor_name} from the game."


def liquidate(stocks_to_liquidate, old_id_name):
    ret_msgs = []
    for s in stocks_to_liquidate:
        # remove from all_stocks CSVs
    
        df = pd.read_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index_col='name')
        df = df.drop(index=[s])
        df.to_csv(f"{SEASON_ID}/all_stocks_dynamic.csv", index='name')

        df = pd.read_csv(f"{SEASON_ID}/all_stocks_static.csv", index_col='name')
        df = df.drop(index=[s])
        df.to_csv(f"{SEASON_ID}/all_stocks_static.csv", index='name')

        # remove from transactions history
        transac_hist = pd.read_csv(f"{SEASON_ID}/transactions_history.csv")
        transac_hist = transac_hist.astype({"stock_id": int,"quantity":float})
        transac_hist['datetime'] = pd.to_datetime(transac_hist['datetime'], format="ISO8601")
        transac_hist = transac_hist.drop(transac_hist[transac_hist["stock_id"] == s].index)
        transac_hist.to_csv(f"{SEASON_ID}/transactions_history.csv", index=None)

        # remove from price history 
        df = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv")
        df = df.drop(df[df["stock_id"] == s].index)
        df.to_csv(f"{SEASON_ID}/stock_prices_history.csv", index=None)

        ret_msgs.append(f"{old_id_name[s]} has gone bankrupt and has disappeared from the market!")
    return ret_msgs

def get_id_name():
    with open(f"{SEASON_ID}/id_name.json") as json_file:
        id_name = json.load(json_file)
        id_name = {int(k):v for k,v in id_name.items()}
    return id_name

def get_name_id():
    with open(f"{SEASON_ID}/name_id.json") as json_file:
        name_id = json.load(json_file)
        name_id = {k:int(v) for k,v in name_id.items()}
    return name_id


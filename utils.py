from csv import writer
from datetime import datetime, timedelta
from math import ceil
import pandas as pd
from constants import name_id, id_name


def get_stock_by_id(name: int) -> pd.Series:
    assert isinstance(name, int)
    df_s = pd.read_csv("all_stocks_static.csv", index_col='name')
    df_d = pd.read_csv("all_stocks_dynamic.csv", index_col='name')
    if name not in df_s.index or name not in df_d.index:
        return None
    x_s = df_s.loc[name,:]
    x_d = df_d.loc[name,:]
    ret = pd.concat([x_s, x_d])
    return ret


def get_investor_by_name(name: str) -> pd.Series:
    df = pd.read_csv("all_investors.csv", index_col='name')
    x = df.loc[name,:]
    return x


def get_portfolio(buyer_name: str) -> pd.DataFrame:
    buyer_portfolio = pd.read_csv(f'portfolios/{buyer_name}.csv', index_col='stock_name')
    return buyer_portfolio


def get_balance(investor_name: str) -> float:
    investor = get_investor_by_name(investor_name)
    return round(investor.cash_balance,2)


def get_stock_value_timedelta(stock_name, td: timedelta, history_time_filtered=None):
    # if history_time_filtered is not None, td will be ignored

    if isinstance(stock_name, str):
        stock_name = name_id[stock_name.lower()]
    if history_time_filtered is None:
        d = datetime.now() - td
        history = pd.read_csv("stock_prices_history.csv", index_col='update_id')
        history = history.astype({"stock_id": int})
        history['datetime'] = pd.to_datetime(history['datetime'])
        history_time_filtered = history[history['datetime'] >= d]
    assert len(history_time_filtered) > 0

    history_name_time_filtered = history_time_filtered[(history_time_filtered['stock_id'] == stock_name)]
    
    return history_name_time_filtered.iloc[0,:].value


def split_msg(msg, max_len=1999):
    if len(msg) < max_len:
        return [msg]
    else:
        # find indices of '\n'
        indices = [i for i, x in enumerate(msg) if x == "\n" and i<=max_len]
        cut = indices[-1]
        return [msg[:cut+1], *split_msg(msg[cut+1:])]


def split_df(df: pd.DataFrame, pages=3):
    max_rows=ceil(len(df.index)/pages)

    # add blank rows at the end if the length of total df is not divisible by pages
    if len(df.index) < max_rows * pages:
        nb_blank_rows = max_rows * pages - len(df.index)
        for i in range(nb_blank_rows):
            df.loc[-i,:] = [' ',0,' ',0]   # Quick hack since uuids cannot be negative. draw_table will mark these rows as blank

    idx_start = 0
    list_of_dfs = []
    while idx_start < len(df.index):
        list_of_dfs.append(df[idx_start:min(idx_start+max_rows, len(df.index))])
        idx_start+=max_rows
    return list_of_dfs


def append_list_as_row(file_name, list_of_elem):
    # Open file in append mode
    with open(file_name, 'a+', newline='') as write_obj:
        # Create a writer object from csv module
        csv_writer = writer(write_obj)
        # Add contents of list as last row in the csv file
        csv_writer.writerow(list_of_elem)



from datetime import datetime, timedelta
import pandas as pd
from constants import name_id


def get_stock_by_name(name: str) -> pd.Series:
    df_s = pd.read_csv("all_stocks_static.csv", index_col='name')
    df_d = pd.read_csv("all_stocks_dynamic.csv", index_col='name')
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
    return investor.cash_balance


def get_stock_value_timedelta(stock_name, td: timedelta):
    d = datetime.now() - td
    if isinstance(stock_name, str):
        stock_name = name_id[stock_name]

    history = pd.read_csv("stock_prices_history.csv", index_col='update_id')
    history = history.astype({"stock_id": int})
    history['datetime'] = pd.to_datetime(history['datetime'])    
    history = history[(history['stock_id'] == stock_name) & (history['datetime'] <= d)]
    if len(history) <= 0:
        return 0
    return history.iloc[-1,:].value



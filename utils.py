import pandas as pd


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




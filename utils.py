import pandas as pd

from constants import TAX, id_name, name_id


def valuate(stock):
    available_shares = stock.total_shares - stock.sold_shares
    supply_demand_ratio = (stock.total_shares + stock.sold_shares)/(available_shares+0.001)
    intrinsic_value = stock.raw_skill * stock.prestige * stock.trendiness
    return round(supply_demand_ratio * intrinsic_value,2)

def valuate_intrinsic(stock):
    intrinsic_value = stock.raw_skill * stock.prestige * stock.trendiness
    return round(intrinsic_value,2)


def get_stocks_table():
    df1 = pd.read_csv("all_stocks_static.csv", index_col='name')
    df2 = pd.read_csv("all_stocks_dynamic.csv", index_col='name')
    df = pd.concat([df1, df2], axis=1)

    current_name_column = df.apply(lambda x:id_name[x.name], axis=1)
    df.insert(0,'current_name', current_name_column)

    df["value_intrinsic"] = df.apply(valuate_intrinsic, axis=1)
    df["value"] = df.apply(valuate, axis=1)
    df["dividend_yield"] = df.apply(get_dividend_yield_from_stock, axis=1)
    return df


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


def get_net_worth(investor_name: str) -> float:
    investor = get_investor_by_name(investor_name)
    net_worth = investor.cash_balance
    portfolio = get_portfolio(investor_name)
    for s in portfolio.index:
        qty = portfolio.loc[s,'shares_owned']
        stock = get_stock_by_name(s)
        net_worth += qty * valuate(stock)
    return net_worth


def get_dividend_yield(stock_name) -> float:
    return get_dividend_yield_from_stock(get_stock_by_name(stock_name))


def get_dividend_yield_from_stock(stock) -> float:
    div_yield = 0.8*(stock.prestige-1) + 0.2*(stock.trendiness-1)
    return round(div_yield, 2)  # This is a percentage


def add_current_name_col(df):
    df=df.copy()
    cnc = df.apply(lambda x:id_name[x.name], axis=1)
    df.insert(0,'current_name', cnc)
    return df

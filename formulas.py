from datetime import datetime, timedelta
from math import exp
import pandas as pd
from constants import id_name, name_id
from utils import get_investor_by_name, get_portfolio, get_stock_by_id


def valuate_intrinsic(stock):
    intrinsic_value = stock.raw_skill/1000 * stock.prestige * stock.trendiness
    return round(intrinsic_value,2)


def valuate(stock):
    available_shares = stock.total_shares - stock.sold_shares
    supply_demand_ratio = (stock.total_shares + stock.sold_shares)/(available_shares+0.001)
    intrinsic_value = valuate_intrinsic(stock)
    return round(supply_demand_ratio * intrinsic_value,2)


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

def get_net_worth(investor_name: str) -> float:
    investor = get_investor_by_name(investor_name)
    net_worth = investor.cash_balance
    portfolio = get_portfolio(investor_name)
    for s in portfolio.index:
        qty = portfolio.loc[s,'shares_owned']
        stock = get_stock_by_id(s)
        net_worth += qty * valuate(stock)
    return round(net_worth,2)


def get_dividend_yield(stock_name) -> float:
    return get_dividend_yield_from_stock(get_stock_by_id(stock_name))


def get_dividend_yield_from_stock(stock) -> float:
    div_yield = 0.8*(stock.prestige-1) + 0.2*(stock.trendiness-1)
    return round(div_yield, 2)  # This is a percentage


def tax_from_datetime(d):  ##
    now = datetime.now()
    if (now-d) > timedelta(hours=4):
        return 0.05
    elif (now-d) > timedelta(hours=1):
        return 0.1
    else:
        return 0.2


def compute_tax_applied(trade_hist, quantity_to_sell):
    assert quantity_to_sell>0

    # 1-create stack where 1 layer = 1 quantity of shares owned and an associated datetime
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
    
    # 2-Use stack to break down the quantity into smaller parts, with an associated datetime
    left_to_sell = quantity_to_sell
    parts=[]
    for qty,tme in reversed(stack):
        if qty<left_to_sell:
            left_to_sell -= qty
            parts.append([qty,tme])
        else:
            parts.append([left_to_sell,tme])
            break
    assert sum([x[0] for x in parts]) == quantity_to_sell
    
    # 4-calculate final tax%
    combination = [[x/abs(quantity_to_sell),tax_from_datetime(y)] for x,y in parts]
    
    res = sum([x*y for x,y in combination])  # linear combination
    return res

def recency_function(x):
    # Defined for x being a number of days and f(x) being the "recency" of a score made on that day
    return exp((-x*x)/1800)

def topplay_importancy_function(x):
    # f(x) defines the importance of someone's x-th top play
    return exp((-x*x)/1500)

import glob
import pandas as pd
import os 

from utils import valuate


def update_stock(stock: pd.Series):
    df = pd.read_csv("all_stocks_dynamic.csv", index_col='name')
    df.loc[stock.name,:] = stock
    df.to_csv("all_stocks_dynamic.csv", index='name')
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
    ownership_df.to_csv(f'ownerships/{stock_name}.csv', index='investor_name')
    return 


def update_buyer_portfolio(buyer_name, stock_name, quantity):
    # TODO: add date history in portfolio
    buyer_portfolio = pd.read_csv(f'portfolios/{buyer_name}.csv', index_col='stock_name')
    if stock_name in buyer_portfolio.index:
        buyer_portfolio.loc[stock_name,:] += quantity
    else:
        buyer_portfolio.loc[stock_name,:] = quantity
    buyer_portfolio.to_csv(f'portfolios/{buyer_name}.csv', index='stock_name')
    return 


def print_all():
    print("\n\nSTOCKS")
    df1 = pd.read_csv("all_stocks_static.csv", index_col='name')
    df2 = pd.read_csv("all_stocks_dynamic.csv", index_col='name')
    df = pd.concat([df1, df2], axis=1)
    df['value'] = df.apply(valuate, axis=1)
    print(df)

    print('\n\nINVESTORS')
    df = pd.read_csv("all_investors.csv", index_col='name')
    print(df)

    print('\n\nPORTFOLIOS')
    for x in glob.glob("portfolios/*.csv"):
        print(x)
        df = pd.read_csv(x, index_col='stock_name')
        print(df)

    print('\n\nOWNERSHIPS')
    for x in glob.glob("ownerships/*.csv"):
        print(x)
        df = pd.read_csv(x, index_col='investor_name')
        print(df)
    return 


def create_new_investor(name, initial_balance):
    df = pd.read_csv("all_investors.csv", index_col='name')
    df.loc[name,:] = initial_balance
    df.to_csv("all_investors.csv", index='name')

    df = pd.DataFrame(columns=['stock_name','shares_owned'])
    df = df.set_index('stock_name')
    df.to_csv(f'portfolios/{name}.csv', index='stock_name')
    return 


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
    return


def reset_all_trades():
    files = glob.glob('portfolios/*.csv')
    for f in files:
        os.remove(f)
    files = glob.glob('ownerships/*.csv')
    for f in files:
        os.remove(f)    
    return

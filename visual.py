import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import datetime

from constants import name_id, id_name
from formulas import get_stocks_table


def print_all():
    print("\n\nSTOCKS")
    df = get_stocks_table()
    print(df)

    print('\n\nINVESTORS')
    df = pd.read_csv("all_investors.csv", index_col='name')
    print(df)

    # print('\n\nPORTFOLIOS')
    # for x in glob.glob("portfolios/*.csv"):
    #     print(x)
    #     df = pd.read_csv(x, index_col='stock_name')
    #     print(df)

    # print('\n\nOWNERSHIPS')
    # for x in glob.glob("ownerships/*.csv"):
    #     print(x)
    #     df = pd.read_csv(x, index_col='investor_name')
    #     print(df)

    print("\n\nHISTORY")
    df = pd.read_csv("transactions_history.csv", index_col='transaction_id')
    print(df)
    return 


def add_current_name_col(df):
    df=df.copy()
    cnc = df.apply(lambda x:id_name[x.name], axis=1)
    df.insert(0,'current_name', cnc)
    return df



def plot_price_evolution(stocks, since=datetime.timedelta(hours=24)):
    stocks = [name_id[x] if isinstance(x, str) else x for x in stocks]

    sns.set_style(rc={'axes.facecolor':'#333333', 'figure.facecolor':'#aaaaaa'})
    
    # Read csv properly
    df = pd.read_csv("stock_prices_history.csv", index_col='update_id')
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.astype({"stock_id": int})

    # select the requested stocks
    selected_players = df['stock_id']<0  #select none of the indices at the start
    for x in stocks:
        selected_players = selected_players | (df['stock_id']==x)

    # select the requested time period
    start_date = datetime.datetime.now() - since
    selected_period = df['datetime']>start_date

    df = df[selected_players & selected_period]
    if df.empty:
        print(f'No data to plot since {start_date}.')
        return
    
    df[''] = df.apply(lambda x:id_name[x['stock_id']], axis=1)  #naming hack so that the graph looks cleaner
    sns.lineplot(data=df, x='datetime', y='value',hue='').set(xticklabels=[],xlabel='last 24 hours')
    plt.show()


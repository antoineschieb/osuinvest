import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import datetime

from constants import name_id, id_name
from formulas import get_stocks_table
from utils import get_stock_value_timedelta


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


def plot_single_stock_price(stocks, since=datetime.timedelta(hours=24)):
    plt.rcParams["font.family"] = "cursive"
    stocks = [name_id[x] if isinstance(x, str) else x for x in stocks]

    # sns.set_style(rc={'axes.facecolor':'#333333', 'figure.facecolor':'#aaaaaa'})
    sns.set_style('darkgrid')
    
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
    # sns.lineplot(data=df, x='datetime', y='value',hue='').set(xticklabels=[],xlabel=f'last {since}')
    ymin = min(df['value'])
    ymax = max(df['value'])
    d = ymax - ymin
    
    ax = df.plot.area(x='datetime', y='value', color='green',ylim=(ymin-0.2*d, ymax+0.2*d), stacked=False, title=id_name[stocks[0]])
    plt.setp(ax.legend().texts, family='Consolas')
    plt.show()


def beautify_float(a: float) :
    char = '↗' if a>=0 else '↘'
    a *= 100
    return f'{char} {round(a,2)}%'

def print_real_time_stocks_evolution(n_hours=24):
    df = get_stocks_table()
    df['value_previous'] = df.apply(lambda x: get_stock_value_timedelta(x.current_name, datetime.timedelta(hours=n_hours)), axis=1)
    df['placeholder_name'] = df.apply(lambda x: (x.value - x.value_previous)/x.value_previous, axis=1)
    
    df = df.sort_values(by='placeholder_name', ascending=False)
    df['placeholder_name'] = df.apply(lambda x: beautify_float(x.placeholder_name), axis=1)
    df = df.rename(columns={'placeholder_name': f'last_{n_hours}h'})
    print(df[['current_name','value',f'last_{n_hours}h']])
    return 
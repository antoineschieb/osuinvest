import matplotlib
matplotlib.use('agg')  # For asynchronous use
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import datetime
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import datetime

from constants import name_id, id_name
from formulas import get_dividend_yield, get_dividend_yield_from_stock, get_net_worth, get_stocks_table, valuate
from utils import get_balance, get_stock_by_id, get_stock_value_timedelta, split_df



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


def plot_stock(stock_str_name :str, n_hours=24, n_days=0):
    assert isinstance(stock_str_name, str)
    if stock_str_name not in name_id.keys():
        return f'ERROR: Unknown stock "{stock_str_name}"'


    if n_hours==0 and n_days==0:
        n_days = 7

    time_str = f'last '
    if n_days<0 or (n_days==0 and n_hours<1):
        return 'n_days must be >= 0 and n_hours must be >=1'
    
    if n_days>0:
        time_str += f'{n_days} day(s) '
    if n_hours>0:   
        time_str += f'{n_hours} hour(s)'
    

    since=datetime.timedelta(hours=n_hours, days=n_days)
    plt.rcParams["font.family"] = "cursive"
    plt.rcParams.update({'font.size': 10})
    stock = name_id[stock_str_name.lower()] 

    # sns.set_style(rc={'axes.facecolor':'#333333', 'figure.facecolor':'#aaaaaa'})
    sns.set_style('darkgrid')
    
    # Read csv properly
    df = pd.read_csv("stock_prices_history.csv", index_col='update_id')
    df['datetime'] = pd.to_datetime(df['datetime'])
    df = df.astype({"stock_id": int})

    # select the requested stock
    selected_players =(df['stock_id']==stock)

    # select the requested time period
    start_date = datetime.datetime.now() - since
    selected_period = df['datetime']>=start_date

    df = df[selected_players & selected_period]
    if df.empty:
        print(f'No data to plot since {start_date}.')
        return
    
    df[''] = df.apply(lambda x:id_name[x['stock_id']], axis=1)  #naming hack so that the graph looks cleaner
    # sns.lineplot(data=df, x='datetime', y='value',hue='').set(xticklabels=[],xlabel=f'last {since}')
    ymin = min(df['value'])
    ymax = max(df['value'])
    d = ymax - ymin
    
    ax = df.plot.area(x='datetime', y='value', color='green',ylim=(ymin-0.2*d, ymax+0.2*d), stacked=False, title=f'{id_name[stock]} {time_str}')
    plt.setp(ax.legend().texts, family='Consolas')
    plt.savefig(f'plots/{stock_str_name}.png')
    return 0


def beautify_float(a: float) :
    char = '↗' if a>=0 else '↘'
    a *= 100
    return f'{char} {round(a,2)}%'

def print_market(n_hours=0, n_days=0, sortby='value'):
    if n_hours==0 and n_days==0:
        n_days = 7
    
    new_col_str = 'last '
    if n_days<0 or (n_days==0 and n_hours<1):
        return 'n_days must be >= 0 and n_hours must be >=1'
    
    if n_days>0:
        new_col_str += f'{n_days} day(s) '
    if n_hours>0:
        new_col_str += f'{n_hours} hour(s)'
    
    df = get_stocks_table()
    
    history = pd.read_csv("stock_prices_history.csv", index_col='update_id')
    history = history.astype({"stock_id": int})
    history['datetime'] = pd.to_datetime(history['datetime'])

    td = datetime.timedelta(hours=n_hours, days=n_days)
    d = datetime.datetime.now() - td
    history_time_filtered = history[history['datetime'] >= d]
    assert len(history_time_filtered) > 0

    df['value_previous'] = df.apply(lambda x: get_stock_value_timedelta(x.current_name, td, history_time_filtered=history_time_filtered), axis=1)
    df['placeholder_name'] = df.apply(lambda x: (x.value - x.value_previous)/x.value_previous, axis=1)
    df['Dividend yield (%)'] = df.apply(lambda x:get_dividend_yield(x.name), axis=1)

    args_colname = {'value':'value', 'evolution':'placeholder_name','dividend':'Dividend yield (%)'}
    df = df.sort_values(by=args_colname[sortby], ascending=False)

    df['placeholder_name'] = df.apply(lambda x: beautify_float(x.placeholder_name), axis=1)

    df = df.rename(columns={'placeholder_name': new_col_str, 'current_name':'Stock'})
    return df[['Stock','value',new_col_str,'Dividend yield (%)']]
    # ret_str = ret_df.to_string(index=False, col_space=20)
    # return ret_str


def print_profile(investor_name):
    df = pd.read_csv("all_investors.csv", index_col='name')
    if investor_name not in df.index:
        return f'ERROR: Unknown investor "{investor_name}"'

    cash_balance = df.loc[investor_name, 'cash_balance']
    
    pf = pd.read_csv(f'portfolios/{investor_name}.csv', index_col='stock_name')
    if not pf.empty:
        stock_column = pf.apply(lambda x:id_name[x.name], axis=1)
        pf.insert(0,'Stock', stock_column)
        pf['Total value ($)'] = pf.apply(lambda x: x.shares_owned * valuate(get_stock_by_id(x.name)), axis=1)
        pf['Dividend yield (%)'] = pf.apply(lambda x:get_dividend_yield_from_stock(get_stock_by_id(x.name)), axis=1)
    
    ret_str = f'Investor: {investor_name}\n\n'
    ret_str += f'Cash balance: ${round(cash_balance,2)}\n\n'
    ret_str += f'Portfolio:\n{pf.to_string(index=False, col_space=20)}\n\n'
    ret_str += f'Total worth: ${round(get_net_worth(investor_name),2)}'
    return ret_str


def print_stock(stock_name):
    if isinstance(stock_name, str):
        stock_name = name_id[stock_name.lower()]
    df = get_stocks_table()
    s = df.loc[stock_name]

    own = pd.read_csv(f"ownerships/{stock_name}.csv", index_col='investor_name')
    own.insert(0,'Investor', own.index)
    own['Proportion owned (%)'] = own.apply(lambda x: round(100*x.shares_owned/s.sold_shares,2), axis=1)

    ret_str = f'Name: {s.current_name}\n'
    ret_str += f'Current value: ${s.value}\n'
    ret_str += f'Dividends: {s.dividend_yield}% /day\n'
    if own.empty:
        ret_str += f'Ownership:\n Noone currently owns any shares of {id_name[stock_name]}!'
    else:
        ret_str += f'Ownership:\n {own.to_string(index=False)}'
    # plot stock could be a nice addition
    return ret_str


def print_leaderboard():
    df = pd.read_csv("all_investors.csv", index_col='name')
    df['Cash balance ($)'] = df.apply(lambda x:round(get_balance(x.name)), axis=1)
    df['Net worth ($)'] = df.apply(lambda x:round(get_net_worth(x.name)), axis=1)
    df = df.sort_values(by='Net worth ($)', ascending=False)
    df.insert(0,'Name', df.index)
    return df[['Name','Net worth ($)','Cash balance ($)']]


def print_investors_gains(dividends_dict):
    df = pd.read_csv("all_investors.csv", index_col='name')
    hist = pd.read_csv("net_worth_history.csv", index_col="log_id")
    ranking = pd.DataFrame(columns=['investor','Net worth ($)','Gains ($)'])
    for inv in df.index:
        hist_filtered = hist[hist['investor']==inv] 
        current = hist_filtered.iloc[-1,:].net_worth
        if len(hist_filtered)<2:
            ranking.loc[len(ranking),:] = [inv, current, 0]
            continue
        previous = hist_filtered.iloc[-2,:].net_worth
        
        gains = current - previous
        current = round(current, 2)
        gains = round(gains, 2)
        ranking.loc[len(ranking),:] = [inv, current, gains]
    ranking = ranking.sort_values(by='Gains ($)', ascending=False)
    ranking['From dividends ($)'] = ranking.apply(lambda x:dividends_dict[x.investor], axis=1)
    ranking['From stocks ($)'] = ranking['Gains ($)'] - ranking['From dividends ($)']
    return ranking.to_string(index=False, col_space=20)


def draw_table(df: pd.DataFrame, filename: str, fontsize:int, rows_per_page: int):
    plt.rcParams.update({'font.size': fontsize})
    df['row_index'] = range(1, len(df)+1)
    list_of_dfs = split_df(df, rows_per_page)
    ret_files = []
    
    for page,df in enumerate(list_of_dfs):
        df = df.reindex(index=df.index[::-1])
        # set the number of rows and cols for our table
        rows = rows_per_page
        cols = len(list(df.columns)) - 1   # -1 because we have one hidden column (row_index)

        # first, we'll create a new figure and axis object
        figsize_x = 18
        figsize_y = 1*rows
        
        fig, ax = plt.subplots(figsize=(figsize_x,figsize_y))

        # create a coordinate system based on the number of rows/columns
        ax.set_ylim(0, rows+1)  # 1 more row for header
        ax.set_xlim(0, cols)
        fig.set_facecolor('#111111')

        for row in range(rows):
            d = df.iloc[row,:]
            row_index = d.row_index
            d = d.drop(labels=['row_index'])

            if not isinstance(d.name, str) and d.name <= 0:  #skip blank rows  # str d.name means we are in a $lb
                continue

            for i,elem in enumerate(d):
                (ha,x,weight,s) = ('left', i+0.05,'bold',f'{int(row_index)}. {elem}') if i==0 else ('right', i+1,'normal',elem)
                t = ax.text(x=x, y=row+0.5, s=s, va='center', ha=ha, weight=weight)
                
                t.set_color('white')
                if isinstance(elem, str):
                    if elem[0] == '↗':
                        t.set_color('green')
                    elif elem[0] == '↘':
                        t.set_color('red')
                    elif row_index==1 and i==0:
                        t.set_color('gold')
                    elif row_index==2 and i==0:
                        t.set_color('silver')
                    elif row_index==3 and i==0:
                        t.set_color('darkgoldenrod')

        df = df.drop(columns=['row_index'])

        # Add column headers
        for i,title in enumerate(df.columns):  # Drop hidden columns
            if len(title)>10 and ' ' in title:
                index = title.index(' ')
                title = title[:index] + '\n' + title[index:]
            (ha,x) = ('left', i+0.05) if i==0 else ('right', i+1)
            ax.text(x, rows+0.5, title, weight='bold', ha=ha).set_color('white')

        # Plot small lines
        for row in range(rows):
            ax.plot(
                [0, cols + 1],
                [row, row],
                ls='--',
                lw='.5',
                c='grey'
            )
        # line to separate header from data
        ax.plot([0, cols + 1], [rows, rows], lw='2', c='white')
        ax.axis('off')

        fig.set_size_inches(figsize_x,figsize_y)
        dest_file = f'{filename}{page}.png'
        plt.savefig(dest_file,bbox_inches='tight',dpi=40)
        plt.close()
        ret_files.append(dest_file)
    return ret_files

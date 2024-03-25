from datetime import datetime, timedelta
import pandas as pd
from constants import SEASON_ID, name_id, id_name
from formulas import compute_tax_applied, valuate, get_dividend_yield
from utils import get_investor_by_name, get_portfolio, get_stock_by_id
from routines import update_buyer, update_stock, log_transaction


def calc_price(buyer, stock, quantity: float, return_tax=False):
    share_price = valuate(stock)

    if quantity > 0:
        transaction_price = round(share_price * quantity, 2)
        # check if buyer has enough cash
        if transaction_price > buyer.cash_balance:
            return f'ERROR: {buyer.name} does not have enough cash (${int(buyer.cash_balance)}) to perform this transaction (${transaction_price}).'
        
        # check if enough shares are available for sale
        if stock.total_shares - stock.sold_shares < quantity:
            return f'ERROR: The total number of available shares {stock.total_shares - stock.sold_shares} is not sufficient to perform this transaction.'
    elif quantity < 0:
        # check if seller has enough shares, and then compute transaction price (with tax)
        portfolio = get_portfolio(buyer.name)
        if stock.name not in portfolio.index:
            return f'ERROR: {buyer.name} does not have any {id_name[stock.name]} shares yet.'

        if portfolio.loc[stock.name,'shares_owned'] < abs(quantity):
            return f'ERROR: {buyer.name} does not have enough {id_name[stock.name]} shares ({portfolio.loc[stock.name,"shares_owned"]}) to perform this transaction.'
        
        trade_hist = get_trade_history(buyer.name, stock.name)
        tax = compute_tax_applied(trade_hist, abs(quantity))
        transaction_price = round(share_price * quantity * (1-tax), 2)
    else:
        return f'ERROR: Quantity traded can not be zero.'
    if return_tax:
        return transaction_price, tax
    else:    
        return transaction_price


def buy_stock(buyer_name: str, stock_name, quantity: float):
    if isinstance(stock_name, str):
        if stock_name not in name_id.keys():
            return f'ERROR: Unknown stock "{stock_name}"'
        stock_name = name_id[stock_name.lower()]
    if stock_name not in id_name.keys():
        return f'ERROR: Unknown stock ID: {stock_name}'    
    stock_name = int(stock_name)

    buyer = get_investor_by_name(buyer_name)
    stock = get_stock_by_id(stock_name)
    transaction_price = calc_price(buyer, stock, quantity)
    if isinstance(transaction_price, str):  # Error
        return transaction_price  

    buyer.cash_balance -= transaction_price
    update_buyer(buyer)
    
    stock.sold_shares += quantity
    update_stock(stock)

    log_transaction(buyer_name, stock_name, quantity)

    return f"{buyer_name} has just {'bought' if quantity>0 else 'sold'} {abs(quantity)} share(s) of **{id_name[stock_name]}** for ${abs(transaction_price)} !"


def sell_stock(buyer_name: str, stock_name: str, quantity: float):
    buy_stock(buyer_name, stock_name, -quantity)
    return


def pay_all_dividends():
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    ret_str = 'Paying all dividends...\n'
    ret_dict = {}
    for investor_name in df.index:        
        portfolio = get_portfolio(investor_name)
        investor = get_investor_by_name(investor_name)
        sum_of_dividends = 0
        for s in portfolio.index:
            qty = portfolio.loc[s,'shares_owned']
            if qty <=0:
                continue
            stock = get_stock_by_id(s)
            volume = qty * valuate(stock)
            if stock.sold_shares == 0:
                raise ValueError
            dividend = round(get_dividend_yield(s) * 0.01 * volume, 2)
            investor.cash_balance += dividend
            sum_of_dividends += dividend
        ret_str += f'{investor_name} received ${round(sum_of_dividends,2)} of total dividends today!\n'
        ret_dict[investor_name] = round(sum_of_dividends,2)
        update_buyer(investor)
    return ret_str, ret_dict


def get_trade_history(buyer_name, stock_id):
    history = pd.read_csv(f"{SEASON_ID}/transactions_history.csv", index_col='transaction_id')
    history = history.astype({"stock_id": int})
    history['datetime'] = pd.to_datetime(history['datetime'], format="ISO8601")
    filtered = history[(history['investor']==buyer_name) & (history['stock_id']==stock_id)]
    quantities = list(filtered['quantity'])
    datetimes = list(filtered['datetime'])
    return list(zip(quantities, datetimes))


def add_pending_transaction(investor, stock_id, quantity):
    df = pd.read_csv(f"{SEASON_ID}/confirmations.csv", index_col="investor")
    df['datetime'] = pd.to_datetime(df['datetime'], format="ISO8601")   
    df.loc[investor,:] = [stock_id,quantity,datetime.now()]
    df.to_csv(f"{SEASON_ID}/confirmations.csv", index="investor")
    return 

def find_transaction(investor):
    df = pd.read_csv(f"{SEASON_ID}/confirmations.csv", index_col="investor")
    df['datetime'] = pd.to_datetime(df['datetime'], format="ISO8601")   
    
    # First, filter only transactions < 5mins
    df = df[datetime.now() - df['datetime'] < timedelta(minutes=5)]
    
    # Then find the pending transaction
    if investor not in df.index:
        return None, None
    stock_id,quantity,_ = df.loc[investor,:]

    # Remove it, and export
    df = df.drop(investor, axis=0)
    df.to_csv(f"{SEASON_ID}/confirmations.csv", index="investor")
    return stock_id,quantity

def remove_transaction_from_pending(investor):
    df = pd.read_csv(f"{SEASON_ID}/confirmations.csv", index_col="investor")
    df['datetime'] = pd.to_datetime(df['datetime'], format="ISO8601")
    # Remove it, and export
    if investor not in df.index:
        return None
    df = df.drop(investor, axis=0)
    df.to_csv(f"{SEASON_ID}/confirmations.csv", index="investor")
    return True


def check_for_alerts():
    ret_strs = []
    df_alerts = pd.read_csv(f"{SEASON_ID}/alerts.csv", index_col="alert_id")
    df_alerts = df_alerts.astype({"stock": int})
    indices_to_drop = []
    for x in df_alerts.index:
        # Conveniently, we store investor's discord uuid and not investor's in-game name so it's easier to ping them
        investor, stock_id, is_greater_than, value = df_alerts.loc[x,:]
        
        current_value = valuate(get_stock_by_id(int(stock_id)))
        if is_greater_than:
            if current_value > value:
                ret_strs.append(f'<@{investor:.0f}> {id_name[stock_id]} is now > {value}')
                indices_to_drop.append(x)
        else:
            if current_value < value:
                ret_strs.append(f'<@{investor:.0f}> {id_name[stock_id]} is now < {value}')
                indices_to_drop.append(x)
        df_alerts = df_alerts.drop(index=indices_to_drop)
    df_alerts.to_csv(f"{SEASON_ID}/alerts.csv", index="alert_id")
    return ret_strs
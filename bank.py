from datetime import datetime
import pandas as pd
from constants import TAX, name_id, id_name
from formulas import compute_tax_applied, valuate, get_dividend_yield
from utils import get_investor_by_name, get_portfolio, get_stock_by_name
from routines import update_buyer, update_buyer_portfolio, update_stock, update_stock_ownership, log_transaction


def buy_stock(buyer_name: str, stock_name, quantity: float):

    if isinstance(stock_name, str):
        stock_name = name_id[stock_name]
    
    buyer = get_investor_by_name(buyer_name)
    stock = get_stock_by_name(stock_name)
    share_price = valuate(stock)
    
    if quantity > 0:
        transaction_price = round(share_price * quantity, 2)
        # check if buyer has enough cash
        if transaction_price > buyer.cash_balance:
            return f'ERROR: {buyer_name} does not have enough cash (${buyer.cash_balance}) to perform this transaction (${transaction_price}).'
        
        # check if enough shares are available for sale
        if stock.total_shares - stock.sold_shares < quantity:
            return f'ERROR: The total number of available shares {stock.total_shares - stock.sold_shares} is not sufficient to perform this transaction.'
    elif quantity < 0:
        # check if seller has enough shares, and then compute transaction price (with tax)
        portfolio = get_portfolio(buyer_name)
        if portfolio.loc[stock_name,'shares_owned'] < abs(quantity):
            return f'ERROR: {buyer_name} does not have enough {id_name[stock_name]} shares ({portfolio.loc[stock_name,"shares_owned"]}) to perform this transaction.'
        
        trade_hist = get_trade_history(buyer_name, stock_name)
        tax = compute_tax_applied(trade_hist, abs(quantity))
        transaction_price = round(share_price * quantity * (1-tax), 2)

    else:
        return f'ERROR: Quantity traded can not be zero.'

    update_stock_ownership(buyer_name, stock_name, quantity)

    update_buyer_portfolio(buyer_name, stock_name, quantity)

    buyer.cash_balance -= transaction_price
    update_buyer(buyer)
    
    stock.sold_shares += quantity
    update_stock(stock)

    log_transaction(buyer_name, stock_name, quantity)

    return f"{buyer_name} has just {'bought' if quantity>0 else 'sold'} {abs(quantity)} share(s) of {id_name[stock_name]} for ${abs(transaction_price)} !"


def sell_stock(buyer_name: str, stock_name: str, quantity: float):
    buy_stock(buyer_name, stock_name, -quantity)
    return


def pay_all_dividends():
    df = pd.read_csv("all_investors.csv", index_col='name')
    ret_str = 'Paying all dividends...\n'
    for investor_name in df.index:        
        portfolio = get_portfolio(investor_name)
        investor = get_investor_by_name(investor_name)
        for s in portfolio.index:
            qty = portfolio.loc[s,'shares_owned']
            if qty <=0:
                continue
            stock = get_stock_by_name(s)
            volume = qty * valuate(stock)
            dividend = round(get_dividend_yield(s)/stock.sold_shares * 0.01 * volume, 2)
            investor.cash_balance += dividend
            ret_str += f'{investor_name} received ${dividend} of dividends from their shares on {id_name[s]}!\n'
        
        update_buyer(investor)
    return ret_str


def get_trade_history(buyer_name, stock_id):
    history = pd.read_csv("transactions_history.csv", index_col='transaction_id')
    history = history.astype({"stock_id": int})
    history['datetime'] = pd.to_datetime(history['datetime']) 
    filtered = history[(history['investor']==buyer_name) & (history['stock_id']==stock_id)]
    quantities = list(filtered['quantity'])
    datetimes = list(filtered['datetime'])
    return list(zip(quantities, datetimes))
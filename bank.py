from rules import TAX
from utils import get_dividend_yield, get_investor_by_name, get_portfolio, get_stock_by_name, valuate
from routines import update_buyer, update_buyer_portfolio, update_stock, update_stock_ownership


def buy_stock(buyer_name: str, stock_name: str, quantity: float):
    
    buyer = get_investor_by_name(buyer_name)
    stock = get_stock_by_name(stock_name)

    share_price = valuate(stock)

    tax = 0 if quantity > 0 else TAX
    transaction_price = round(share_price * quantity * (1-tax), 2)
    
    if transaction_price > 0:
        # check if buyer has enough cash
        if transaction_price > buyer.cash_balance:
            print(f'{buyer_name} does not have enough cash (${buyer.cash_balance}) to perform this transaction (${transaction_price}).')
            return
        
        # check if enough shares are available for sale
        if stock.total_shares - stock.sold_shares < quantity:
            print(f'The total number of available shares {stock.total_shares - stock.sold_shares} is not sufficient to perform this transaction.')
            return
    elif transaction_price < 0:
        # check if seller has enough shares
        portfolio = get_portfolio(buyer_name)
        if portfolio.loc[stock_name,'shares_owned'] < abs(quantity):
            print(f'{buyer_name} does not have enough {stock_name} shares ({portfolio.loc[stock_name,"shares_owned"]}) to perform this transaction.')
            return  

    update_stock_ownership(buyer_name, stock_name, quantity)

    update_buyer_portfolio(buyer_name, stock_name, quantity)


    buyer.cash_balance -= transaction_price
    update_buyer(buyer)
    
    stock.sold_shares += quantity
    update_stock(stock)

    print(f"{buyer_name} has just {'bought' if quantity>0 else 'sold'} {abs(quantity)} share(s) of {stock_name} for ${abs(transaction_price)} !")
    return 


def sell_stock(buyer_name: str, stock_name: str, quantity: float):
    buy_stock(buyer_name, stock_name, -quantity)
    return


def pay_dividends(investor_name: str):
    portfolio = get_portfolio(investor_name)
    investor = get_investor_by_name(investor_name)

    for s in portfolio.index:
        qty = portfolio.loc[s,'shares_owned']
        stock = get_stock_by_name(s)
        volume = qty * valuate(stock)
        dividend = round(get_dividend_yield(s) * 0.01 * volume, 2)
        investor.cash_balance += dividend
        print(f'{investor_name} received ${dividend} of dividends from their shares on {s}!')
    
    update_buyer(investor)
    return 


# def cash_in_dividends(self):
#     for k,v in self.portfolio.items():
#         # k.valuate() ?
#         percentage = k.get_dividend_return()
#         value_of_shares = v * k.share_price
#         self.cash_balance += percentage*value_of_shares


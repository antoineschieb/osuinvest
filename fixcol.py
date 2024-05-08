from datetime import datetime
from utils import get_portfolio
from visual import print_market
import pandas as pd
from constants import SEASON_ID


df = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv")
df['datetime'] = pd.to_datetime(df['datetime'], format="ISO8601").dt.floor('s')
df['stock_id'] = df.apply(lambda x:int(x.stock_id), axis=1)
df.to_csv(f"{SEASON_ID}/stock_prices_history.csv", index=None)



df = pd.read_csv(f"{SEASON_ID}/net_worth_history_continuous.csv")
df['datetime'] = pd.to_datetime(df['datetime'], format="ISO8601").dt.floor('s')
df.to_csv(f"{SEASON_ID}/net_worth_history_continuous.csv", index=None)


df = pd.read_csv(f"{SEASON_ID}/net_worth_history.csv")
df['datetime'] = pd.to_datetime(df['datetime'], format="ISO8601").dt.floor('s')
df.to_csv(f"{SEASON_ID}/net_worth_history.csv", index=None)


df = pd.read_csv(f"{SEASON_ID}/transactions_history.csv")
df['datetime'] = pd.to_datetime(df['datetime'], format="ISO8601").dt.floor('s')
df['stock_id'] = df.apply(lambda x:int(x.stock_id), axis=1)
df.to_csv(f"{SEASON_ID}/transactions_history.csv", index=None)
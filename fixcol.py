from datetime import datetime
from utils import get_portfolio
from visual import print_market
import pandas as pd
from constants import SEASON_ID

# Alerts
df = pd.read_csv(f"{SEASON_ID}/alerts.csv")
df = df.astype({"stock": int})
df = df.drop(columns="alert_id")
df.to_csv(f"{SEASON_ID}/alerts.csv", index=None)


# NW Hist
df = pd.read_csv(f"{SEASON_ID}/net_worth_history.csv")
df = df.drop(columns="log_id")
df.to_csv(f"{SEASON_ID}/net_worth_history.csv", index=None)

# Stock Prices Hist
df = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv")
df = df.drop(columns="update_id")
df.to_csv(f"{SEASON_ID}/stock_prices_history.csv", index=None)


# NW Hist Continuous
df = pd.read_csv(f"{SEASON_ID}/net_worth_history_continuous.csv")
df = df.drop(columns="log_id")
df.to_csv(f"{SEASON_ID}/net_worth_history_continuous.csv", index=None)

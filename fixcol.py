from datetime import datetime
from utils import get_portfolio
from visual import print_market
import pandas as pd
from constants import SEASON_ID

# Read column types properly
history = pd.read_csv(f"{SEASON_ID}/transactions_history.csv")
history = history.astype({"stock_id": int})
history['datetime'] = pd.to_datetime(history['datetime'], format="ISO8601")
history = history.drop(columns="transaction_id")
history.to_csv(f"{SEASON_ID}/transactions_history.csv", index=None)
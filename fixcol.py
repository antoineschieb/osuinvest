import pandas as pd
from constants import SEASON_ID
from datetime import datetime
from utils import get_stock_value_timedelta

transac_hist = pd.read_csv(f"{SEASON_ID}/transactions_history.csv", index_col='transaction_id')
transac_hist = transac_hist.astype({"stock_id": int,"quantity":float})
transac_hist['datetime'] = pd.to_datetime(transac_hist['datetime'], format="ISO8601")
transac_hist['timedelta'] = datetime.now() - transac_hist['datetime']

history = pd.read_csv(f"{SEASON_ID}/stock_prices_history.csv", index_col='update_id')
history = history.astype({"stock_id": int})
history['datetime'] = pd.to_datetime(history['datetime'], format="ISO8601")
col = transac_hist.apply(lambda x: x.quantity * get_stock_value_timedelta(x.stock_id,x.timedelta, history=history), axis=1)
transac_hist.insert(3,'price', col)
transac_hist = transac_hist.drop(columns=['timedelta'])
transac_hist.to_csv(f"{SEASON_ID}/transactions_history.csv", index='transaction_id')
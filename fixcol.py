import pandas as pd

from constants import SEASON_ID

df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
df['zero_tax_alerts'] = 0
df.to_csv(f"{SEASON_ID}/all_investors.csv", index='name')
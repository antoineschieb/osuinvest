from math import exp
import numpy as np
import pandas as pd
from constants import SEASON_ID

from visual import add_current_name_col


def compute_prestige(x: pd.Series) -> float:
    p = 2.0 * x.badges +\
        2.0 * x.rank_peak +\
        1.5 * x.scores_first_count +\
        1.0 * x.replays_watched_by_others +\
        0.5 * x.follower_count +\
        0.1 * x.mapping_follower_count +\
        0.1 * x.support_level +\
        0.1 * x.maximum_combo
    return p


def compute_hype(x: pd.Series) -> float:
    h = 3.0 * x.rank_current_to_mean +\
        3.0 * x.topplay_activity +\
        2.0 * x.rank_current_to_worst +\
        2.0 * x.rank_current_to_highest_ever +\
        1.5 * x.last_month_activity +\
        1.5 * x.activity +\
        0.4 * x.scores_recent_count +\
        0.3 * x.is_silenced +\
        0.2 * x.is_active        
    return h


def compute_prestige_and_hype(new_season_id=None):
    if new_season_id is not None:
        season_id = new_season_id
    else:
        season_id = SEASON_ID

    df_raw = pd.read_csv(f"{season_id}/player_data_raw.csv", index_col='id')
    df = (df_raw-df_raw.mean())/df_raw.std()
    df = df.astype(float).fillna(0)
    df = add_current_name_col(df)

    df['prestige'] = df.apply(compute_prestige, axis=1)
    df['prestige'] = (df['prestige']-df['prestige'].mean())/df['prestige'].std()
    df['prestige'] = 1+np.power(2.0,df['prestige'])

    df['hype'] = df.apply(compute_hype, axis=1)
    df['hype'] = (df['hype']-df['hype'].mean())/df['hype'].std()
    df['hype'] = 1+np.power(1.5, df['hype'])

    df['current_pp'] = df_raw['pp']
    return df[['current_pp','prestige','hype']]

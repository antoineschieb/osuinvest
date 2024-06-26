import pandas as pd
import ossapi
from datetime import datetime, timezone
from datetime import timedelta as td
from scipy import stats
import random
from tqdm import tqdm
from math import log

from formulas import recency_function, topplay_importancy_function 
from osuapi import api, top_i
from utils import get_pilimg_from_url


def get_username(uuid):
    return api.user(uuid, mode='osu').username


def create_id_list(country="FR", topN=50, proba=1.0):
    L = list()
    for i in tqdm(range(topN)):
        if random.random() > proba:
            continue
        L.append(top_i(i, country))
    return L





def fix_peppys_playcount_list(user_monthly_playcounts):
    """
    Adds recent months where the user didnt play and logs them as months with 0 playcount
    """
    L = []
    for x in user_monthly_playcounts:
        s = x.start_date
        c = x.count
        L.append([s,c])

    prev_s = L[-1][0]
    while prev_s.year != datetime.now().year or prev_s.month != datetime.now().month:
        # while last one is not current month, add entry [previous_start_date+1month, 0]
        if prev_s.month<12:
            new_s = datetime(day=1, month=prev_s.month + 1, year=prev_s.year)
        else:
            new_s = datetime(day=1, month=1, year=prev_s.year + 1)
        L.append([new_s, 0])
        prev_s = L[-1][0]
    return L


def get_last_month_activity(uuid):
    user_recent_activity = api.user_recent_activity(uuid, limit=50)
    user_recent_activity = [x for x in user_recent_activity if isinstance(x, ossapi.models.RankEvent)]
    return len(user_recent_activity)

def get_topplay_activity(uuid):
    user_scores = api.user_scores(uuid, type='best', limit=100, mode='osu')
    now = datetime.now(timezone.utc)
    age_of_topplays = [(now - x.created_at).days for x in user_scores]  # in days
    recency_scores = [recency_function(x) for x in age_of_topplays]
    topplay_activity = sum([topplay_importancy_function(i) * recency_scores[i] for i in range(len(recency_scores))])
    return topplay_activity


def all_user_info(u):
    # u = api.user(uuid, mode='osu')

    # update cache osu
    im = get_pilimg_from_url(u.avatar_url)
    im.save(f"plots/osuavatar_{u.id}.png")

    all_info = {}
    # first add all u.statistics
    for stat_str in ['pp','hit_accuracy','play_count','play_time','replays_watched_by_others','maximum_combo']:
        all_info[stat_str] = eval(f"u.statistics.{stat_str}")

     # Then all the u.
    for stat_str in ['badges','follower_count','is_active','is_silenced','join_date','mapping_follower_count',
                     'scores_first_count','scores_recent_count','support_level','rank_highest.rank',
                     'rank_history.data','monthly_playcounts']:
        all_info[stat_str] = eval(f"u.{stat_str}")
    
    # Post-process all the info so that each entry is a number, and not str or list
    all_info['badges'] = len(all_info['badges'])
    all_info['is_active'] = int(all_info['is_active'])
    all_info['join_date'] = (datetime.now(tz=timezone.utc) - all_info['join_date']).days   # Days since account creation
    all_info['id'] = u.id
    all_info['is_silenced'] = 0 if all_info['is_silenced'] is None else 1

    # log columns
    all_info['replays_watched_by_others'] = log(1+all_info['replays_watched_by_others'])
    all_info['follower_count'] = log(1+all_info['follower_count'])
    all_info['mapping_follower_count'] = log(1+all_info['mapping_follower_count'])
    all_info['scores_first_count'] = log(1+all_info['scores_first_count'])
    all_info['scores_recent_count'] = log(1+all_info['scores_recent_count'])

    # rank related stuff
    rank_highest_ever = all_info['rank_highest.rank']
    rank_current = all_info['rank_history.data'][-1]
    rank_mean = sum(all_info['rank_history.data'])/len(all_info['rank_history.data'])
    rank_worst = min(all_info['rank_history.data'])

    all_info['rank_peak'] = -log(rank_highest_ever, 4)
    all_info['rank_current_to_worst'] = (rank_worst - rank_current)/rank_mean
    all_info['rank_current_to_mean'] = (rank_mean - rank_current)/rank_mean
    all_info['rank_current_to_highest_ever'] = (rank_highest_ever - rank_current)/rank_current

    del all_info['rank_highest.rank']
    del all_info['rank_history.data']

    # Activity from monthly playcounts
    monthly_playcounts = fix_peppys_playcount_list(all_info['monthly_playcounts'])
    pc1 = monthly_playcounts[-1][1]
    pc2 = monthly_playcounts[-2][1]
    pc3 = monthly_playcounts[-3][1]
    activity = 0.1*pc3 + 0.3*pc2 + 0.6*pc1
    all_info['activity'] = activity
    
    del all_info['monthly_playcounts']

    # More specific activity stats
    # /!\ requires more requests /!\
    all_info['last_month_activity'] = get_last_month_activity(u.id)  

    all_info['topplay_activity'] = get_topplay_activity(u.id)


    return all_info

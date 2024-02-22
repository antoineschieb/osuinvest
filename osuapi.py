import pandas as pd
from creds import client_id, client_secret, redirect_uri
import ossapi
from datetime import datetime, timezone
from datetime import timedelta as td
from scipy import stats
import random
from tqdm import tqdm

from math import log 

api = ossapi.Ossapi(client_id, client_secret, redirect_uri)


def get_username(uuid):
    return api.user(uuid).username


def get_join_date(uuid):
    return api.user(uuid).join_date


def create_id_list(country="FR", topN=50, proba=1.0):
    L = list()
    for i in tqdm(range(topN)):
        if random.random() > proba:
            continue
        L.append(top_i(i, country))
    return L


def top_i(i, country):
    return api.ranking("osu", ossapi.RankingType.PERFORMANCE, country=country, cursor=ossapi.Cursor(page=(i // 50) + 1)).ranking[
        i % 50].user.id


def update_rename():
    name_id = {}
    id_name = {}
    fridlisttop50  = create_id_list()
    for x in fridlisttop50:
        un = get_username(x)
        name_id[un] = x
        id_name[x] = un
    return name_id, id_name


def get_playcounts(uuid, start=datetime.now()-td(days=20*365), end=datetime.now() - td(days = datetime.now().day - 1) ):
    ret = []
    for x in api.user(uuid).monthly_playcounts:
        if start <= x.start_date <= end:
            ret.append(x)
    y = []
    for elem in ret:
        y.append(elem.count)
    if datetime.now().year == end.year and datetime.now().month == end.month:
        y[-1]= int(y[-1] * (30.42/datetime.now().day))  # assuming player keeps playing at the same rate
    # make estimation to correct current month
    return y


def get_activity_from_playcounts(pc_list, months_range=(None,None)):
    x = list(range(len(pc_list)))
    b,a = months_range
    if b>a:
        a,b = b,a
    b = len(x) - b if b else None
    a = len(x) - a if a else None

    pcs_considered = pc_list[a:b]
    volume = sum(pcs_considered)/len(pc_list[a:b])
    proportion = sum(pcs_considered) / sum(pc_list)
    slope = (stats.linregress(x=list(range(len(pcs_considered))), y=pcs_considered)).slope
    return (volume,proportion,slope)

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


def all_user_info(uuid=5189431):
    u = api.user(uuid)

    all_info = {}
    # first add all u.statistics
    for stat_str in ['pp','hit_accuracy','play_count','play_time','replays_watched_by_others','maximum_combo']:
        all_info[stat_str] = eval(f"u.statistics.{stat_str}")

     # Then all the u.
    for stat_str in ['badges','follower_count','is_active','is_silenced','join_date','mapping_follower_count',
                     'scores_first_count','scores_recent_count','support_level','rank_highest.rank',
                     'rank_history.data','monthly_playcounts']:
        all_info[stat_str] = eval(f"u.{stat_str}")

    #TODO: add these later: 
        # monthly_playcounts:     (trendiness)
        # replays_watched_counts: (trendiness)
    
    # Post-process all the info so that each entry is a number, and not str or list
    all_info['badges'] = len(all_info['badges'])
    all_info['is_active'] = int(all_info['is_active'])
    all_info['join_date'] = (datetime.now(tz=timezone.utc) - all_info['join_date']).days   # Days since account creation
    all_info['id'] = uuid
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

    return all_info


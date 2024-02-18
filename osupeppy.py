import pandas as pd
from creds import client_id, client_secret, redirect_uri
import ossapi
from datetime import datetime
from datetime import timedelta as td
from scipy import stats
import random
from tqdm import tqdm

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


def all_user_info(uuid=5189431):
    u = api.user(uuid)

    all_info = {}
    # first add all u.statistics
    for stat_str in ['pp','hit_accuracy','playcount','play_time','replays_watched_by_others','maximum_combo']:
        all_info[stat_str] = eval(f"u.statistics.{stat_str}")

    
    return all_info

if __name__ == "__main__":
    # french_players = create_id_list(country="FR", topN=300)
    # df = pd.DataFrame(columns=['username','userID','pp','acc','pc','seniority','a3','a6','a12'])
    df = pd.read_csv("result.csv")
    french_players = df["userID"]
    for uuid in tqdm(french_players):
        [pp, acc, pc, seniority, a3, a6, a12] = all_user_info(uuid)
        uname = get_username(uuid)
        new_entry = {'username': uname,
                     'userID':uuid,
                     'pp':pp,
                     'acc':acc,
                     'pc':pc,
                     'seniority':seniority,
                     'a3':a3,
                     'a6':a6,
                     'a12':a12,}
        df.loc[len(df.index)] = new_entry
    print(df)
    df.to_csv('result.csv')

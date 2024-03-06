import json
from osuapi import api, top_i
import csv
import os


def new_season(new_season_id, N=52):
    """
    Remember to change the SEASON_ID variable in constants.py after running this
    """
    if os.path.exists(f'{new_season_id}/'):
        raise ValueError("Season already exists!")
    
    # 0 - create portoflios/ and ownerships/ (empty)
    os.mkdir(f'{new_season_id}/')
    os.mkdir(f'{new_season_id}/portfolios/')
    os.mkdir(f'{new_season_id}/ownerships/')

    # 1 - create name_id and id_name jsons
    id_name = {}
    name_id = {}
    for i in range(N):
        uuid = top_i(i, country='FR')
        u = api.user(uuid, mode='osu')
        current_username = u.username
        id_name[uuid] = current_username
        name_id[current_username.lower()] = uuid
        for n in u.previous_usernames:
            name_id[n.lower()] = uuid
    with open(f"{new_season_id}/name_id.json", "w") as fp:
        json.dump(name_id , fp)
    with open(f"{new_season_id}/id_name.json", "w") as fp:
        json.dump(id_name , fp) 

    # 2 - create all necessary CSVs (empty) except player_data_raw
    with open(f"{new_season_id}/alerts.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['alert_id','investor','stock','greater','value'])

    with open(f"{new_season_id}/all_investors.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["name","cash_balance"])

    with open(f"{new_season_id}/all_stocks_dynamic.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["name","total_shares","sold_shares"])

    with open(f"{new_season_id}/all_stocks_static.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["name","raw_skill","trendiness","prestige"])

    with open(f"{new_season_id}/confirmations.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["investor","stock_id","quantity","datetime"])

    with open(f"{new_season_id}/net_worth_history.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["log_id","investor","net_worth","datetime"])

    with open(f"{new_season_id}/stock_prices_history.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["update_id","stock_id","value","datetime"])
    
    with open(f"{new_season_id}/transactions_history.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['transaction_id','investor','stock_id','quantity','datetime'])

    # Finally, change season_id in config json
    cfg = {}
    cfg['SEASON_ID'] = str(new_season_id)
    with open(f"config.json", "w") as fp:
        json.dump(cfg , fp) 
    return


if __name__=='__main__':
    new_season('beta1', N=100)
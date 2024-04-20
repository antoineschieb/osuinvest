import argparse
from datetime import datetime
import json
from osuapi import api, top_i
import csv
import os


def new_season(new_season_id, N_in=100, N_out=105, season_start_date=None, season_end_date=None, set_as_default=True):

    assert N_in < N_out

    if os.path.exists(f'{new_season_id}/'):
        raise ValueError("Season already exists!")
    
    # 0 - create empty folder
    os.mkdir(f'{new_season_id}/')

    # 1 - create name_id and id_name jsons
    id_name = {}
    name_id = {}
    for i in range(N_in):
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
        writer.writerow(['investor','stock','greater','value'])

    with open(f"{new_season_id}/all_investors.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["name","cash_balance","zero_tax_alerts"])

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
        writer.writerow(["investor","net_worth","datetime"])

    with open(f"{new_season_id}/net_worth_history_continuous.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["investor","net_worth","datetime"])

    with open(f"{new_season_id}/stock_prices_history.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["stock_id","value","datetime"])
    
    with open(f"{new_season_id}/transactions_history.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['investor','stock_id','quantity','price','datetime'])
    
    with open(f"{new_season_id}/zero_tax_alerts.csv", "w", newline='') as file:
        writer = csv.writer(file)
        writer.writerow(['investor','stock','last_bought'])


    #Create empty investors_uuid and uuid_investors
    with open(f"{new_season_id}/uuid_investor.json", "w") as fp:
        json.dump(dict() , fp)
    with open(f"{new_season_id}/investor_uuid.json", "w") as fp:
        json.dump(dict() , fp) 

    #Create season_config.json
    
    try:
        #parse date with '%Y-%m-%d %H:%M:%S' format
        season_start_date = datetime.strptime(season_start_date,'%Y-%m-%d %H:%M:%S')
        season_end_date = datetime.strptime(season_end_date,'%Y-%m-%d %H:%M:%S')
    except Exception as e:
        print(e)
        raise ValueError("Date format must be '%Y-%m-%d %H:%M:%S'")
    
    d = {"N_in":N_in, "N_out":N_out,"season_start_date":season_start_date.strftime('%Y-%m-%d %H:%M:%S'),"season_end_date":season_end_date.strftime('%Y-%m-%d %H:%M:%S')}
    with open(f"{new_season_id}/season_config.json", "w") as fp:
        json.dump(d, fp)


    # Finally, change season_id in config json
    if set_as_default:
        with open(f"config.json") as json_file:
            cfg = json.load(json_file)
        cfg['SEASON_ID'] = str(new_season_id)
        with open(f"config.json", "w") as fp:
            json.dump(cfg , fp) 
        print(f"New season by default is now {new_season_id}")
    return


if __name__=='__main__':
    parser = argparse.ArgumentParser()

    parser.add_argument('season_name')
    parser.add_argument('player_count_in')
    parser.add_argument('player_count_out')
    parser.add_argument('start_date')
    parser.add_argument('end_date')
    

    args = parser.parse_args()
    print(f"Creating new season {args.season_name} with the top {(int(args.player_count_in),int(args.player_count_out))} players \
           starting {args.start_date} and ending {args.end_date}")
    new_season(args.season_name, N_in=int(args.player_count_in), N_out=int(args.player_count_out), season_start_date=args.start_date,season_end_date=args.end_date)
    
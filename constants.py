import json

# FEED_CHANNEL_ID = 854465506428977156  # Antoine's server
# FEED_CHANNEL_ID = 1210628840720695386  # serv des oeufs
FEED_CHANNEL_ID = 1218303570609311926  # osu!Invest FR (beta)


with open(f"config.json") as json_file:
    cfg = json.load(json_file)
    SEASON_ID = cfg['SEASON_ID']

with open(f"{SEASON_ID}/id_name.json") as json_file:
    id_name = json.load(json_file)
    id_name = {int(k):v for k,v in id_name.items()}

with open(f"{SEASON_ID}/name_id.json") as json_file:
    name_id = json.load(json_file)
    name_id = {k:int(v) for k,v in name_id.items()}

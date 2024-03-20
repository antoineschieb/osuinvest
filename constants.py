import json

with open(f"config.json") as json_file:
    cfg = json.load(json_file)
    SEASON_ID = cfg['SEASON_ID']
    FEED_CHANNEL_ID = int(cfg['FEED_CHANNEL_ID'])
    GUILD_ID = int(cfg['GUILD_ID'])
    DETAILS_CHANNEL_ID = int(cfg['DETAILS_CHANNEL_ID'])

with open(f"{SEASON_ID}/id_name.json") as json_file:
    id_name = json.load(json_file)
    id_name = {int(k):v for k,v in id_name.items()}

with open(f"{SEASON_ID}/name_id.json") as json_file:
    name_id = json.load(json_file)
    name_id = {k:int(v) for k,v in name_id.items()}

import json
with open(f"config.json") as json_file:
    cfg = json.load(json_file)
    SEASON_ID = cfg['SEASON_ID']
    FEED_CHANNEL_ID = int(cfg['FEED_CHANNEL_ID'])
    ALERTS_CHANNEL_ID = int(cfg['ALERTS_CHANNEL_ID'])
    GUILD_ID = int(cfg['GUILD_ID'])
    DETAILS_CHANNEL_ID = int(cfg['DETAILS_CHANNEL_ID'])
    ADMINS = cfg['ADMINS']


with open(f"{SEASON_ID}/uuid_investor.json") as json_file:
    uuid_investor = json.load(json_file)
    uuid_investor = {int(k):v for k,v in uuid_investor.items()}

with open(f"{SEASON_ID}/investor_uuid.json") as json_file:
    investor_uuid = json.load(json_file)
    investor_uuid = {k:int(v) for k,v in investor_uuid.items()}

import json
with open(f"config.json") as json_file:
    cfg = json.load(json_file)
    SEASON_ID = cfg['SEASON_ID']
    FEED_CHANNEL_ID = int(cfg['FEED_CHANNEL_ID'])
    ALERTS_CHANNEL_ID = int(cfg['ALERTS_CHANNEL_ID'])
    GUILD_ID = int(cfg['GUILD_ID'])
    DETAILS_CHANNEL_ID = int(cfg['DETAILS_CHANNEL_ID'])
    ADMINS = cfg['ADMINS']

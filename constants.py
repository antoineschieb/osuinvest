import json

FEED_CHANNEL_ID = 854465506428977156  # Antoine's server
# FEED_CHANNEL_ID = 1210628840720695386  # serv des oeufs

with open('id_name.json') as json_file:
    id_name = json.load(json_file)
    id_name = {int(k):v for k,v in id_name.items()}

with open('name_id.json') as json_file:
    name_id = json.load(json_file)
    name_id = {k:int(v) for k,v in name_id.items()}
    

from matplotlib import font_manager
font_prop = font_manager.FontProperties(fname='custom_font\Aller_Bd.ttf')
import json
from constants import SEASON_ID
from osuapi import api, top_i


def update_name_id(name_id, id_name, N=52):
    """
    Updates names : id correspondences for the top N players, taking renames into account. 
    """
    for i in range(N):
        uuid = top_i(i, country='FR')
        u = api.user(uuid)
        current_username = u.username
        id_name[uuid] = current_username
        name_id[current_username.lower()] = uuid
        for n in u.previous_usernames:
            name_id[n.lower()] = uuid
    with open(f"{SEASON_ID}/name_id.json", "w") as fp:
        json.dump(name_id , fp)
    with open(f"{SEASON_ID}/id_name.json", "w") as fp:
        json.dump(id_name , fp) 
    return


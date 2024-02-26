import json
from osuapi import api, top_i


def create_name_id(N=52):  
    """
    Creates names : id correspondences for the top N players, taking renames into account. 
    """
    name_id = {}
    id_name = {}
    for i in range(N):
        uuid = top_i(i, country='FR')
        u = api.user(uuid)
        current_username = u.username
        id_name[uuid] = current_username
        name_id[current_username.lower()] = uuid
        for n in u.previous_usernames:
            name_id[n.lower()] = uuid
    with open("name_id.json", "w") as fp:
        json.dump(name_id , fp)
    with open("id_name.json", "w") as fp:
        json.dump(id_name , fp) 
    return


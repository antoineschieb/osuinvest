import ossapi
from creds import client_id, client_secret

api = ossapi.Ossapi(client_id, client_secret)

def top_i(i, country):
    return api.ranking("osu", ossapi.RankingType.PERFORMANCE, country=country, cursor=ossapi.Cursor(page=(i // 50) + 1)).ranking[
        i % 50].user.id

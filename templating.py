from urllib.request import Request, urlopen
from io import BytesIO
from osuapi import api
import io
import PIL
from matplotlib import pyplot as plt
import datetime
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
import pandas as pd

from constants import name_id, id_name
from formulas import get_stocks_table
from utils import get_stock_value_timedelta
from visual import beautify_float, plot_stock


def get_pilimg_of_pie(x, colors):
    fig, ax = plt.subplots(figsize = (20,20))
    patches, texts = ax.pie(x, colors=colors,
                            textprops={'fontsize': 30})
    for t in texts:
        t.set_horizontalalignment('center')
    pimg = buffer_plot_and_get(fig)
    plt.close()
    return pimg

def get_profile_info_for_stock(uuid):
    u = api.user(uuid)
    url = u.avatar_url
    url = str(url)
    req = Request(
        url=url, 
        headers={'User-Agent': 'Mozilla/5.0'})
    webpage = urlopen(req).read()
    avatar = Image.open(BytesIO(webpage)).convert("RGBA")

    return u.statistics.global_rank,u.statistics.pp,u.statistics.rank['country'],avatar

def buffer_plot_and_get(fig):
    buf = io.BytesIO()
    fig.savefig(buf, transparent=True, bbox_inches='tight')
    buf.seek(0)
    return PIL.Image.open(buf)


def stock_card(playername,global_rank,value,evolution,dividend_yield,pp,country_rank, graph, avatar, pie, shareholders_list, colors):
    def draw_align_right(y, text, fontsize, color=(255,255,255)):
        lgth = draw.textlength(text, font=ImageFont.truetype(file, fontsize))
        draw.text((400-lgth-margin, y), text, font=ImageFont.truetype(file, fontsize), fill=color)
        return
    
    # LOAD MAIN TEMPLATE
    tpl = Image.open('templates/stock_template.png')

    # RESIZE ALL SUBLAYERS
    graph = graph.resize((401,302))
    avatar = avatar.resize((189-18,257-87))
    pie = pie.resize((374-254 +22,388-266 +22))

    # ADD ALL SUBLAYERS (GRAPH, AVATAR, PIE) TO TEMPLATE
    full = Image.new('RGB', (400, 700))
    full.paste(graph, (7,407))
    full.paste(avatar, (18,87))
    full.paste(pie, (254-10,266-10))
    full.paste(tpl, (0, 0), tpl)

    # ALL TEXT
    draw = ImageDraw.Draw(full)
    font = font_manager.FontProperties(family='Aller')
    file = font_manager.findfont(font)

    font_bold = font_manager.FontProperties(family='Aller', weight="bold")
    file_bold = font_manager.findfont(font_bold)


    margin=10
    draw.text((margin, 47), playername, font=ImageFont.truetype(file_bold, 30), fill=(255, 255, 255))
    draw.text((240, 230), f'#{global_rank}', font=ImageFont.truetype(file, 20), fill=(255, 255, 255))

    draw_align_right(60, f'${value}',44)
    clr = (0,255,0) if evolution > 0 else (255,0,0)
    draw_align_right(110, f'({beautify_float(evolution)})',30, color=clr)
    draw_align_right(150,f'Dividends: {dividend_yield}% /day',14, color="#d0db97")
    draw_align_right(200, f'{round(pp)}pp', 20)
    draw_align_right(230, f'#{country_rank}', 20)

    # LITTLE ICONS
    # globe = Image.open('templates/420px-Globe_icon.svg.png')
    globe = Image.open('templates/earth.png')
    globe = globe.resize((22,22))
    full.paste(globe, (214,230), globe)

    flag = Image.open('templates\Flag_of_France.svg.png')
    flag = flag.resize((21,14))
    lgth = draw.textlength(f'#{country_rank}', font=ImageFont.truetype(file, 20))
    full.paste(flag, (400-round(lgth)-margin-21-4, 234))    #326

    # lgth = draw.textlength(text, font=ImageFont.truetype(file, fontsize))
    #     draw.text((400-lgth-margin,

    # TOP SHAREHOLDERS
    draw.text((margin, 280), "Top shareholders", font=ImageFont.truetype(file, 20), fill=(255, 255, 255))
    for i in range(len(shareholders_list)):
        square = Image.new('RGBA', (8,8), colors[i])

        if shareholders_list[i][0] is None:
            txt = f'Nobody owns any shares\nof {playername} yet!'
        else:
            txt = f'{shareholders_list[i][0]} : {shareholders_list[i][1]}'
        draw.text((26, 310 + 20*i), txt, font=ImageFont.truetype(file, 16), fill=(255,255,255))
        full.paste(square, (margin, 310 + 20*i + 6))
    
    return full



def generate_stock_card(stock_str_name, n_hours=24, n_days=0):
    def shorten_shareholders_list(l):
        if len(l) == 0:
            return [[None,1]]
        l = sorted(l, key=lambda x:x[1], reverse=True)
        if len(l)<=3:
            return l
        else:
            l_main = l[:3]
            l_others = l[3:]
            others_element = ['others',sum([x[1] for x in l_others])]
            l_main.extend([others_element])
            return l_main

    assert isinstance(stock_str_name, str)
    if stock_str_name.lower() not in name_id.keys():
        return f'ERROR: Unknown stock "{stock_str_name}"'
    stock_id = name_id[stock_str_name.lower()]
    
    if n_hours==0 and n_days==0:
        n_days = 7
    if n_days<0 or (n_days==0 and n_hours<1):
        return 'n_days must be >= 0 and n_hours must be >=1'
    time_str = f'Last '
    if n_days>0:
        time_str += f'{n_days} day(s) '
    if n_hours>0:   
        time_str += f'{n_hours} hour(s)'

    
    df = get_stocks_table()
    s = df.loc[stock_id]
    
    td = datetime.timedelta(hours=n_hours, days=n_days)
    value_previous=get_stock_value_timedelta(s.current_name, td)
    evolution = (s.value - value_previous)/value_previous

    own = pd.read_csv(f"ownerships/{stock_id}.csv", index_col='investor_name')
    shareholders_list = [[x, own.loc[x].shares_owned] for x in own.index]
    shareholders_list = shorten_shareholders_list(shareholders_list)

    ret_path = plot_stock(s.current_name.lower(), n_days=n_days, n_hours=n_hours)
    graph = Image.open(ret_path)

    global_rank,pp,country_rank,avatar = get_profile_info_for_stock(stock_id)

    colors= ['#181D27'] if shareholders_list[0][0] is None else ["darkred","darkgreen","goldenrod","darkblue"]
    pie = get_pilimg_of_pie([x[1] for x in shareholders_list], colors)


    card = stock_card(s.current_name,global_rank,s.value,evolution,s.dividend_yield,pp,country_rank,graph, avatar, pie, shareholders_list, colors)
    
    file_path = f'plots/card_{stock_id}.png'
    card.save(file_path)
    return file_path

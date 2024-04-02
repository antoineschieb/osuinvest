from math import sqrt
from urllib.request import Request, urlopen
from io import BytesIO

import mplcyberpunk
import numpy as np
np.seterr(divide='ignore', invalid='ignore')
from game_related import api
import io
import PIL
from matplotlib import pyplot as plt
import datetime
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont
import pandas as pd
import matplotlib
from formulas import get_dividend_yield_from_stock, get_net_worth, valuate
from utils import get_avatar_from_osu_cache, get_id_name, get_name_id, get_ownership, get_portfolio, get_stock_by_id, beautify_time_delta

from constants import SEASON_ID
from visual import get_stocks_table
from utils import get_pilimg_from_url, get_stock_value_timedelta
from visual import beautify_float_percentage, plot_stock


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
    u = api.user(uuid, mode='osu')
    return u.statistics.global_rank,u.statistics.pp,u.statistics.rank['country']

def buffer_plot_and_get(fig):
    buf = io.BytesIO()
    fig.savefig(buf, transparent=True, bbox_inches='tight')
    buf.seek(0)
    return PIL.Image.open(buf)


def stock_card(playername,global_rank,value,evolution,dividend_yield,pp,country_rank, graph, td, avatar, pie, shareholders_list, colors):
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
    full.paste(graph, (12,400))
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
    fontsize = int(26*sqrt(12/(len(playername)))) if len(playername)>12 else 30
    draw.text((margin, 47), playername, font=ImageFont.truetype(file_bold, fontsize), fill=(255, 255, 255))
    draw.text((240, 230), f'#{global_rank}', font=ImageFont.truetype(file, 20), fill=(255, 255, 255))

    draw_align_right(40, f'${value}',44)
    clr = (0,255,0) if evolution > 0 else (255,0,0)
    draw_align_right(90, f'({beautify_float_percentage(evolution)})',30, color=clr)
    draw_align_right(130,f'over the last {beautify_time_delta(td.total_seconds(), include_seconds=False)}',13, color=clr)
    draw_align_right(150,f'Dividends: {dividend_yield}% /day',14, color="#d0db97")
    draw_align_right(200, f'{round(pp)}pp', 20)
    draw_align_right(230, f'#{country_rank}', 20)

    # LITTLE ICONS
    # globe = Image.open('templates/420px-Globe_icon.svg.png')
    globe = Image.open('templates/earth.png')
    globe = globe.resize((22,22))
    full.paste(globe, (214,230), globe)

    flag = Image.open('templates/Flag_of_France.svg.png')
    flag = flag.resize((21,14))
    lgth = draw.textlength(f'#{country_rank}', font=ImageFont.truetype(file, 20))
    full.paste(flag, (400-round(lgth)-margin-21-4, 234))    #326

    # TOP SHAREHOLDERS
    draw.text((margin, 280), "Top shareholders", font=ImageFont.truetype(file, 20), fill=(255, 255, 255))
    for i in range(len(shareholders_list)):
        square = Image.new('RGBA', (8,8), colors[i])

        if shareholders_list[i][0] is None:
            txt = f'Nobody owns any shares\nof {playername} yet!'
        else:
            txt = f'{shareholders_list[i][0]} : {shareholders_list[i][1]}'
        fontsize = int(16*sqrt(17/(len(txt)))) if len(txt)>17 else 16
        draw.text((26, 310 + 20*i), txt, font=ImageFont.truetype(file, fontsize), fill=(255,255,255))
        full.paste(square, (margin, 310 + 20*i + 6))
    
    return full



def generate_stock_card(stock_str_name, n_hours=0, n_days=7):
    def shorten_shareholders_list(l):
        if len(l) == 0:
            return [[None,1]]
        l = sorted(l, key=lambda x:x[1], reverse=True)
        if len(l)<=3:
            return l
        else:
            l_main = l[:3]
            l_others = l[3:]
            others_element = ['others', round(sum([x[1] for x in l_others]),1)]
            l_main.extend([others_element])
            return l_main

    assert isinstance(stock_str_name, str)
    name_id = get_name_id()
    if stock_str_name.lower() not in name_id.keys():
        return f'ERROR: Unknown stock "{stock_str_name}"'
    stock_id = name_id[stock_str_name.lower()]
    
    if n_hours==0 and n_days==0:
        n_days = 7
    if n_days<0 or (n_days==0 and n_hours<1):
        return 'ERROR: n_days must be >= 0 and n_hours must be >=1'
    
    df = get_stocks_table()
    s = df.loc[stock_id]
    
    td = datetime.timedelta(hours=n_hours, days=n_days)
    value_previous=get_stock_value_timedelta(s.current_name, td)
    evolution = 0 if value_previous==0 else (s.value - value_previous)/value_previous

    own = get_ownership(stock_id)
    shareholders_list = [[x, own.loc[x].shares_owned] for x in own.index]
    shareholders_list = shorten_shareholders_list(shareholders_list)

    ret_path, td = plot_stock(s.current_name.lower(), n_days=n_days, n_hours=n_hours)
    graph = Image.open(ret_path)

    global_rank,pp,country_rank = get_profile_info_for_stock(stock_id)
    avatar = get_avatar_from_osu_cache(stock_id)

    colors= ['#181D27'] if shareholders_list[0][0] is None else ["darkred","darkgreen","goldenrod","darkblue"]
    pie = get_pilimg_of_pie([x[1] for x in shareholders_list], colors)

    card = stock_card(s.current_name,global_rank,s.value,evolution,s.dividend_yield,pp,country_rank,graph, td, avatar, pie, shareholders_list, colors)
    
    file_path = f'plots/card_{stock_id}.png'
    card.save(file_path)
    return file_path


########################################################################################


def get_nw_plot(dates, vals, default=10000):
    
    if len(dates) == 0 or len(vals) == 0:
        vals = [default]
        dates = [datetime.datetime.now()]

    min_v = min(vals)
    max_v = max(vals)
    delta = max_v - min_v + 0.1

    fig, ax = plt.subplots(figsize=(10,5))
    fig.patch.set_alpha(0.0)
    ax.patch.set_alpha(0.0)

    matplotlib.rcParams['axes.prop_cycle'] = matplotlib.cycler(color=["gray", "gold", "#181D27","#00ff00"])
    matplotlib.rcParams['axes.formatter.useoffset'] = False
    ax.plot(dates, vals, color="#fffb00")

    # markers for highest and lowest
    if len(dates) != 0:
        ax.plot(dates[vals.index(max_v)], max_v, marker=7, markersize=20, color='lime')
        ax.annotate(int(1000*(round(max_v,3))),  xy=(dates[vals.index(max_v)], max_v+0.12*delta), color='lime',fontsize=24)
        ax.plot(dates[vals.index(min_v)], min_v, marker=6, markersize=20, color='red')
        ax.annotate(int(1000*(round(min_v,3))),  xy=(dates[vals.index(min_v)], min_v-0.12*delta), color='red',fontsize=24)

    ax.set_xticklabels([])
    ax.set_xticks([])

    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.spines['bottom'].set_color('white')
    ax.spines['left'].set_color('white')

    ax.tick_params(axis='y', colors='white', labelsize=20)
    ax.set_ylabel('Net worth (k$)', fontsize=20, color='white')
    ax.set_xlabel('date', fontsize=20, color='white')
    plt.ylim(min_v-0.15*delta, max_v+0.15*delta)
    plt.xlim(min(dates), max(dates))

    # will only display selected dates, here first and last
    display_dates = [date.strftime('%d-%b %H:%M') if date == min(dates) or date == max(dates) else "" for date in dates]

    plt.xticks(dates, display_dates, color='white', fontsize='20')

    mplcyberpunk.make_lines_glow(ax)
    mplcyberpunk.add_gradient_fill(ax, alpha_gradientglow=(0.05,0.2), gradient_start='bottom')

    fig_path = "plots/net_worth.png"
    fig.savefig(fig_path, transparent=False, bbox_inches='tight')
    plt.close()
    return fig_path
    
def shorten_portfolio(pf,N):
    if len(pf)<=N:
        return pf
    sum_of_all_other_stocks = pf.iloc[N:,:].sum(axis=0, numeric_only=True).copy()   #sum from 3rd to last
    pf = pf.iloc[:N].copy()
    pf.loc['Others',:] = round(sum_of_all_other_stocks, 1)
    return pf



def profile_card(investor_name, avatar, graph_filepath, current_networth, cash_balance, pf, server_rank, server_total_investors):
    def draw_align_right(y, text, fontsize, color=(255,255,255), font='regular'):
        if font=='bold':
            font=ImageFont.truetype(file_bold, fontsize)
        elif font=='regular':
            font=ImageFont.truetype(file, fontsize)
        lgth = draw.textlength(text, font=ImageFont.truetype(file, fontsize))
        draw.text((400-lgth-margin, y), text, font=font, fill=color)
        return
    
    margin=10
    # LOAD MAIN TEMPLATE
    tpl = Image.open('templates/profile_400_fond_rouge.png')

    # RESIZE ALL SUBLAYERS
    
    


    # ADD ALL SUBLAYERS (GRAPH, AVATAR, PIE) TO TEMPLATE
    full = Image.new('RGB', (400, 700), color="#181D27")
    if avatar is not None:
        avatar = avatar.resize((102,102))
        full.paste(avatar, (27,80), avatar)
    full.paste(tpl, (0, 0), tpl)
    graph = Image.open(graph_filepath).resize((360,180))
    full.paste(graph, (margin,210), graph)
    

    # ALL TEXT
    draw = ImageDraw.Draw(full)
    font = font_manager.FontProperties(family='Aller')
    file = font_manager.findfont(font)

    font_bold = font_manager.FontProperties(family='Aller', weight="bold")
    file_bold = font_manager.findfont(font_bold)

    fontsize = int(30*sqrt(14/(len(investor_name)))) if len(investor_name)>14 else 30
    draw.text((margin, 40), investor_name, font=ImageFont.truetype(file_bold, fontsize), fill=(255, 255, 255))
    appendix='th'
    if server_rank==1:
        appendix='st'
    elif server_rank==2:
        appendix='nd'
    elif server_rank==3:
        appendix='rd'

    draw_align_right(40, f'{server_rank}{appendix} /{server_total_investors}',40, font='bold')
    draw_align_right(90, f'${current_networth}',34,color='gold')
    draw_align_right(130, f'Total net worth', 16, color='gold')
    draw_align_right(160, f'${cash_balance} from cash balance',16)
    draw_align_right(180, f'${current_networth - cash_balance} from stocks value',16)
    # DRAW PORTFOLIO TXT
    id_name = get_id_name()
    for i,x in enumerate(pf.index):
        s = pf.loc[x]
        shares_owned = float(s['Shares owned'])
        draw.text((30, 450 + 24*i), x if x=='Others' else id_name[x], font=ImageFont.truetype(file, 15))
        draw.text((210, 450 + 24*i), str(round(shares_owned,1)), font=ImageFont.truetype(file, 15))
        draw.text((295, 450 + 24*i), f"${round(s['Total value ($)'])}", font=ImageFont.truetype(file, 15))


    # PORTFOLIO HEADERS

    draw.text((30, 420), 'Stock', font=ImageFont.truetype(file_bold, 14))
    draw.text((210, 420), 'Shares', font=ImageFont.truetype(file_bold, 14))
    draw.text((295, 420), "Total value", font=ImageFont.truetype(file_bold, 14))

    
    return full

def generate_profile_card(investor_name: str, avatar:Image, n_hours: int=0, n_days: int=7):  # take avatar as parameter too, dince it's easier to retrieve it in dsbot.py
    df = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    if investor_name not in df.index:
        return f'ERROR: Unknown investor "{investor_name}"'
    
    if n_hours==0 and n_days==0:
        n_days = 7
    if n_days<0 or (n_days==0 and n_hours<1):
        return 'ERROR: n_days must be >= 0 and n_hours must be >=1'
    

    # CASH BALANCE
    cash_balance = df.loc[investor_name, 'cash_balance']

    # PORTFOLIO
    pf = get_portfolio(investor_name, short=True)
    id_name = get_id_name()
    if not pf.empty:
        stock_column = pf.apply(lambda x:id_name[x.name], axis=1)
        pf.insert(0,'Stock', stock_column)
        pf['Total value ($)'] = pf.apply(lambda x: x.shares_owned * valuate(get_stock_by_id(x.name)), axis=1)
        pf['Dividend yield (%)'] = pf.apply(lambda x:get_dividend_yield_from_stock(get_stock_by_id(x.name)), axis=1)
        pf = pf.rename(columns={'shares_owned':'Shares owned'})
        pf = pf.sort_values(by='Total value ($)', ascending=False)
        pf = shorten_portfolio(pf, 9)

    
    # NET WORTH HISTORY
    hist = pd.read_csv(f"{SEASON_ID}/net_worth_history_continuous.csv")
    hist_filtered_investor = hist[hist.investor==investor_name].copy()
    hist_filtered_investor["datetime"] = pd.to_datetime(hist_filtered_investor["datetime"], format="ISO8601")
    td = datetime.timedelta(hours=n_hours, days=n_days)
    hist_filtered_investor_time = hist_filtered_investor[hist_filtered_investor['datetime'] > datetime.datetime.now() - td]

    all_net_worth_vals = [round(x/1000,5) for x in hist_filtered_investor_time["net_worth"]]
    all_net_worth_dates = [x for x in hist_filtered_investor_time["datetime"]]

    graph_filepath = get_nw_plot(all_net_worth_dates, all_net_worth_vals)

    all_invs = pd.read_csv(f"{SEASON_ID}/all_investors.csv", index_col='name')
    all_invs['net_worth'] = all_invs.apply(lambda x:get_net_worth(x.name), axis=1)
    all_invs = all_invs.sort_values(by='net_worth', ascending=False)
    
    server_rank = list(all_invs.index).index(investor_name)+1
    server_total_investors = len(all_invs.index)

    card = profile_card(investor_name, avatar, graph_filepath, round(get_net_worth(investor_name)), round(cash_balance), pf, server_rank, server_total_investors)
    file_path = f'plots/card_{investor_name}.png'
    card.save(file_path)
    return file_path

import time
from datetime import datetime
from bs4 import BeautifulSoup as BS
import requests
import re
from tqdm import tqdm
import jsonlines
import json
import sys
# push

START_DATE = "0109"
END_DATE = "0112"

over18_url = "https://www.ptt.cc/ask/over18"
target_url = "https://www.ptt.cc/bbs/Beauty/index.html"

MONTH_STR = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
              "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

JSONFILENAME = "all_article"

# enter the page
payload = {
   'from': '/bbs/Beauty/index.html',
   'yes':'yes'
}
# https://www.ptt.cc/bbs/Beauty/index3647.html # first 2022 01/01 
# https://www.ptt.cc/bbs/Beauty/index3955.html # last 2022 12/31
# [3647, 3955]

def num2str(num): return str(num).strip().zfill(2)
MONTH_NUM = list(map(num2str, [1,2,3,4,5,6,7,8,9,10,11,12]))
MONTH_DICT = dict(zip(MONTH_STR, MONTH_NUM))

def write_jsonl(content, filename='all_article', mode='a'):
    with jsonlines.open(f'{filename}.jsonl', mode=mode) as writer:
        writer.write(content)
    return None

def pass_over18(link, over18_url=over18_url, payload=payload):
    rs = requests.session()
    res = rs.post(over18_url, data=payload)
    content = rs.get(link).text

    return content

def get_time(link, year=2023):
    tag, date = 0, None
    content = pass_over18(link)
    soup = BS(content, 'html.parser')
    # 作者 看板 標題 時間
    # artitle = soup.find_all(class_="article-meta-value") 
    span = soup.find_all(class_="article-meta-value", limit=4)[3]
    # print(span, len(span), type(span))
    if str(year) not in span.string:
        # print(f"No {year} in ", span)
        pass
    else:
        tag=1
    timer = span.string
    timer = timer.replace('  ',' ') # prevent like Jan  1 -> [Jan, , 1]
    month, day = timer.split(' ')[1:3]
    date = MONTH_DICT[month]+day.zfill(2) # 0101, 0112, 1231
    return tag, date

def get_prev_page(content): # in new way we did not use it
    soup = BS(content, 'html.parser')
    # 最舊 ‹ 上頁 下頁 › 最新
    previous_page_button = soup.find_all(class_="btn wide", limit=2)[1] 
    # if '上頁' in button.string:
    button_link = previous_page_button.get('href')
    full_link = "https://www.ptt.cc/" + button_link
    return full_link

# More quickly to check whether this page is what I want years period
def check_first_last_time_logic(article, year=2022):
    # 快速檢查頭尾頁面逐筆文章資料
    ctr_first=0
    # deal with those might be delete article
    while not article[0+ctr_first].find('a'):
        ctr_first+=1
    get_first_link = article[0+ctr_first].find('a').get('href')
    
    ctr_last=0
    # deal with those might be delete article
    while not article[-1+ctr_last].find('a') or "公告" in article[-1+ctr_last].find('a').string:
        ctr_last-=1
    get_last_link = article[-1+ctr_last].find('a').get('href')

    # print(get_first_link, get_last_link)
    first_tag, first_date = get_time("https://www.ptt.cc/" + get_first_link, year=year)
    last_tag, last_date = get_time("https://www.ptt.cc/" + get_last_link, year=year)
    return (first_tag or last_tag)
     
def check_is_not_announce(content, year=2022):
    # 排除 [公告] 等文章
    date_set = set()
    soup = BS(content, 'html.parser')
    # check if it is not [公告] then
    article = soup.find_all(class_='title')
    if check_first_last_time_logic(article, year=year):
        for ctr, ele in enumerate(article):
            try:
                name = ele.find('a').string
                link = ele.find('a').get('href')        
                table = re.split(r"\[|\]", name)[1]
                if table not in ['公告']:
                    isinyear, date = get_time("https://www.ptt.cc/" + link, year=year)
                    date_set.add(date)
                    if isinyear:
                        add = { "date" : date,
                                "title": name,
                                "url"  : "https://www.ptt.cc/" + link}
                        # print(ctr, add)
                        write_jsonl(add, filename=JSONFILENAME, mode='a')
            # This content be delete
            except:
                print("Delete", ele.string)

    return date_set

def fillzero(date):
    month, day = date
    return str(month).zfill(2)+str(day).zfill(2)

def get_time_index_map(time_set, index, dct):
    for time in time_set:
        if time not in dct:
            dct[time] = [index,index]
        else:
            dct[time][1] = index
    return dct

def first_check(index, mode='first'): # first, last check
    while True:
        date_set = set()
        # first check the first and last article date and year in the page
        full_link = f"https://www.ptt.cc/bbs/Beauty/index{index}.html"
        content = pass_over18(full_link, over18_url=over18_url, payload=payload)
        soup = BS(content, 'html.parser')
        date_lst = soup.find_all(class_="date")
        date0 = fillzero(list(map(num2str, date_lst[0].string.split('/'))))
        date1 = fillzero(list(map(num2str, date_lst[-1].string.split('/'))))
        date_set.add(date0)
        date_set.add(date1)
        print(date_set)
        if ("0101" in date_set) and ("1231" in  date_set):
            return index
        elif mode=="first":
            index-=1
        elif mode=="last":
            index+=1
            
def get_date_set(r_ent):
    date_set = set()
    add_data_list = list()
    for ctr, r_ent_ in enumerate(r_ent):
        try:
            title = r_ent_.find(class_="title").find('a')
            name = title.string
            link = title.get('href')
            table = re.split(r"\[|\]", name)[1]

            date = r_ent_.find(class_="meta").find(class_='date').string
            date = date.strip().split('/')
            date = fillzero(date)                    
            date_set.add(date)

            if table not in '公告':
                add_data = { "date" : date,
                        "title": name,
                        "url"  : "https://www.ptt.cc/" + link}
                add_data_list.append(add_data)
                if ctr%10==0:print(ctr, add_data)
                # write_jsonl(add_data, filename=JSONFILENAME, mode='a')
        # This content be delete
        except:
            print("Delete", r_ent_.string)
            
    return add_data_list, date_set


# push
def get_datatime_range(date1, date2, year1=2022, year2=2022):
    # date1 year1 : start date
    # date2 year2 : end date
    S_date = date1+str(year1) 
    E_date = date2+str(year2) 
    S = datetime.strptime(S_date, "%m%d%Y").date()
    E = datetime.strptime(E_date, "%m%d%Y").date()
    # print(S_date, E_date, S, E, E-S)
    # res = [S_date + datetime.timedelta(days=idx) for idx in range(E-S)]
    return S,E
 
def get_take_index(r_ent, start_date=START_DATE, end_date=END_DATE):
    S, E = get_datatime_range(start_date, end_date)
    # print(S>E, S<E)
    take_index = list()
    part_link_list = [ele.find('a').get('href') for ele in r_ent]
    for link in part_link_list:
        isinyear, date = get_time("https://www.ptt.cc/" + link, year=2022)
        date = datetime.strptime(date+str(2022), "%m%d%Y").date()
        if S<=date<=E:
            take_index.append(1)
        else:
            take_index.append(0)
    # take_index = [get_time("https://www.ptt.cc/" + link, year=2022)[0] 
                # for link in part_link_list]
    return take_index 

def get_date_index(date_index_map, start=START_DATE, end=END_DATE):
    return [date_index_map[START_DATE][0], date_index_map[END_DATE][1]]

def load_jsonl():
    with jsonlines.open('all_article.jsonl', 'r') as json_file:
        json_list = list(json_file)
    return json_list

def load_json(filename='date_index_map'):
    with open(f'{filename}.json', 'r') as file:
        json_file = json.load(file)
        return json_file

def get_image_url(soup):
    # get rid of the url which postfix is not in jpg, jpeg, png, gif
    image_url_list = []
    article = soup.find_all(class_='bbs-screen bbs-content')# all content
    for ele in article:
        for a in ele.find_all('a'):
            url = a.get('href')
            check_prefix_logic = url.split(':')[0].lower() in ['https', 'http']
            check_postfix_logic = url.split('.')[-1].lower() in ['jpg', 'jpeg', 'png', 'gif']
            if check_prefix_logic and check_postfix_logic:
                image_url_list.append(url)
    return image_url_list

def check_like_or_boo(soup):
    # return boolean 0, 1
    # 0 : is boo article
    # 1 : is like article
    # -1: is so so article
    like_ctr, boo_ctr = 0, 0
    # hl push-tag : find like
    # f1 hl push-tag : find boo
    user_id = soup.find(class_="article-meta-value").string.split(' ')[0] # first is author
    comments = soup.findAll(True, {'class':{"hl push-tag", "f1 hl push-tag"}})
    for comment in comments:
        comment_string = comment.string
        if '推' in comment_string:
            like_ctr+=1
        elif '噓' in comment_string:
            boo_ctr+=1
    if boo_ctr>like_ctr:return 0, user_id
    if boo_ctr<like_ctr:return 1, user_id
    if boo_ctr==like_ctr:return -1, user_id

def main_crawl():
    # first check the prev page is 2022 0101
    # second check the post page is 2022 1231
    date_index_dict = dict()
    START_INDEX  = first_check(3642, mode='first')
    END_INDEX  = first_check(3950, mode='last')
    print(START_INDEX, END_INDEX)

    for index in tqdm(range(START_INDEX, END_INDEX+1)):
        # take a break time
        if index%30:time.sleep(0.5)

        full_link = f"https://www.ptt.cc/bbs/Beauty/index{index}.html"
        # https://www.ptt.cc/bbs/Beauty/index.html
        content = pass_over18(full_link, over18_url=over18_url, payload=payload)
        
        if index in [START_INDEX, END_INDEX]:
            date_set = check_is_not_announce(content, year=2022)
        else:
            soup = BS(content, 'html.parser')
            r_ent = soup.find_all(class_="r-ent")
            add_data_list, date_set = get_date_set(r_ent)
            for add_data in add_data_list:
                write_jsonl(add_data, filename=JSONFILENAME, mode='a')
        
        date_index_dict = get_time_index_map(date_set, index, date_index_dict)
        del date_set
        
    with open('date_index_map.json', 'w') as file:
        json.dump(date_index_dict, file, indent=4)
    return None

def main_push(start_date, end_date, year1=2022, year2=2022):
    print("In main_push")
    json_list = load_jsonl()
    date_index_map = load_json()
    YEAR1, YEAR2 = year1, year2
    START_DATE, END_DATE = start_date, end_date
    record_dict = dict() # record ctr about (like, boo)
    all_like, all_boo = 0, 0
    # get start index and end index
    index_range = get_date_index(date_index_map, start=START_DATE, end=END_DATE) 

    for index in tqdm(range(index_range[0], index_range[1]+1)):
        url = f"https://www.ptt.cc/bbs/Beauty/index{index}.html"
        content = pass_over18(url)
        soup = BS(content, 'html.parser')
        r_ent = soup.find_all(class_="r-ent")
        
        # give the logical to check which article in the first or last will be catch
        if index in index_range: 
            take_index = get_take_index(r_ent, start_date=START_DATE, end_date=END_DATE)
        else: take_index = [1 for _ in range(len(r_ent))]

        for take, ele in zip(take_index, r_ent):
            # 0 : X
            # 1 : 爆
            # 2 : 個位數
            # 3 : 十位數 
            boo_like_text = ele.findAll(True, {"class":{"hl f0", "hl f1", "hl f2", "hl f3"}})
            user_id = ele.find(class_="author").string
            # [boo_ctr, like_ctr]
            if take:
                if  user_id not in record_dict:record_dict[user_id]=[0,0]
                
                for  ele_ in boo_like_text:
                    if ele_.string: # filter the None
                        # (boo)
                        if 'X' in ele_.string:
                            record_dict[user_id][0]+=1
                            all_boo+=1
                        # (like) other is string number or the string 爆 
                        else:
                            record_dict[user_id][1]+=1
                            all_like+=1
                    else:
                        print(ele_)
    # print(record_dict)
    boo_list = sorted(record_dict.items(), key=lambda x:(x[1][0], x[0]), reverse=True)[:10]
    like_list = sorted(record_dict.items(), key=lambda x:(x[1][1], x[0]), reverse=True)[:10]
    
    final_dct = dict()
    final_dct["all_like"] = all_like
    final_dct["all_boo"] = all_boo
    for rank, like in enumerate(like_list, start=1):
        final_dct[f"like {rank}"] = {"user_id":like[0], "count":like[1][1]}
    for rank, boo in enumerate(boo_list, start=1):
        final_dct[f"boo {rank}"] = {"user_id":boo[0], "count":boo[1][0]}
    with open(f'push_{START_DATE}_{END_DATE}.json', 'w') as file:
        json.dump(final_dct, file, indent=4)

    print(final_dct)
    return None

def main_popular(start_date, end_date, year1=2022, year2=2022):
    print("In main_popular")
    json_list = load_jsonl()
    date_index_map = load_json()
    YEAR1, YEAR2 = year1, year2
    START_DATE, END_DATE = start_date, end_date
    record_link_list = list() # record part link about (popular)
    all_popular = 0
    index_range = get_date_index(date_index_map, start=START_DATE, end=END_DATE)
    record_dict = {"number_of_popular_articles":0, "image_urls":[]}
    for index in tqdm(range(index_range[0], index_range[1]+1)):
        url = f"https://www.ptt.cc/bbs/Beauty/index{index}.html"
        content = pass_over18(url)
        soup = BS(content, 'html.parser')
        r_ent = soup.find_all(class_="r-ent")
        for ele in r_ent:
            boo_like_text = ele.findAll(True, {"class":{"hl f0", "hl f1", "hl f2", "hl f3"}})
            user_id = ele.find(class_="author").string
            part_link = ele.find('a').get('href')

            for boo_like in boo_like_text:
                if ("爆" in boo_like.string):
                    record_link_list.append(part_link)
                    print(boo_like, part_link)
                    full_link = f"https://www.ptt.cc/{part_link}"
                    content = pass_over18(full_link, over18_url=over18_url, payload=payload)
                    soup = BS(content, 'html.parser')
                    record_dict['number_of_popular_articles']+=1
                    record_dict['image_urls'].extend(get_image_url(soup))
    with open(f'popular_{START_DATE}_{END_DATE}.json', 'w') as file:
        json.dump(record_dict, file, indent=4)
    return record_dict

get_main_process = {
    "crawl":main_crawl,
    "push":main_push,
    "popular":main_popular
    }


# python XX.py crawl 
# python XX.py push 0101 1231
# python XX.py popular 0105 0228 
#
if __name__=="__main__":
    if len(sys.argv[1:])==1:
        # crawl
        get_main_process[sys.argv[1]]()
    elif len(sys.argv[1:])==3:
        # push, popular
        START_DATE, END_DATE = sys.argv[2], sys.argv[3]
        get_main_process[sys.argv[1]](START_DATE, END_DATE)
    elif len(sys.argv[1:])==4:
        # keyword
        pass

    print(len(sys.argv[1:]), sys.argv)
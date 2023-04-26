from flask import Flask, render_template, request, send_file, send_from_directory, make_response
from flask_paginate import Pagination, get_page_parameter
import requests as req
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import xlsxwriter
from wordcloud import WordCloud
from konlpy.tag import Kkma
from collections import Counter
import os
import dataframe_image as dfi
import sys
from concurrent.futures import ThreadPoolExecutor


app = Flask(__name__)
app.debug =True

############################################# Crawl ######################################################3
# 1. Today's politics, economics, society, digital alticles from the website which is named daum, page 1 to 400 - Daum
def news_article(page_url):
    response = req.get(page_url, headers={
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15'
    })
    soup = BeautifulSoup(response.text, 'html.parser')
    articles = soup.select("div.box_etc div.cont_thumb")
    return articles

categories = ['politics', 'economic', 'society', 'digital']
target_articles = {category: [] for category in categories}

for category in categories:
    with ThreadPoolExecutor(max_workers=20) as executor:
        article_pages = [f"https://news.daum.net/breakingnews/{category}?page={i}" for i in range(1, 401)]
        article_lists = list(executor.map(news_article, article_pages))
        for index, articles in enumerate(article_lists):
            for item in articles:
                article_title = item.select("strong.tit_thumb a")[0].text
                article_press = item.select("span.info_news")[0].text
                article_txt = item.select("span.link_txt")[0].text.replace('\n', '').replace('...', '').replace('앵커', '').lstrip()
                article_link = item.find("a")['href']

                article = {}
                article['type'] = category
                article['title'] = article_title
                article['txt'] = article_txt
                article['press'] = article_press
                article['link'] = article_link

                target_articles[category].append(article)

dfs = []
for category, articles in target_articles.items():
    df = pd.DataFrame(data=articles)
    dfs.append(df)

news = pd.concat(dfs).reset_index(drop=True)
news[['press', 'time']] = news['press'].str.split('·', n=1, expand=True)
today = datetime.today()
news['time'] = news['time'].apply(lambda x: datetime.strptime(f"{today.date()} {x}:00", '%Y-%m-%d %H:%M:%S'))
news = news[['type','title','txt','press','time','link']]

# 2. Today's view top 1 per press - Naver
topview_url = "https://news.naver.com/main/ranking/popularDay.naver"

response = req.get(topview_url, headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15'})
soup = BeautifulSoup(response.text, 'html.parser')
articles = soup.select("div.rankingnews_box")

target_articles = {}

for index, item in enumerate(articles):
    article_title = item.select("ul.rankingnews_list a")[0].text
    article_press = item.select("strong.rankingnews_name")[0].text
    article_time = item.select("span.list_time")[0].text
 
    article = {}
    article['type'] = 'top1_view'
    article['title'] = article_title
    article['press'] = article_press
    article['time'] = article_time
    
    target_articles[index] = article

targets = list()
for value in target_articles.values():
    targets.append(value)
df_artc_top_view = pd.DataFrame(data=targets)
df_artc_top_view

#3. Today's comments top 1 per press - Naver
topcomm_url = "https://news.naver.com/main/ranking/popularMemo.naver"

response = req.get(topcomm_url, headers={'User-Agent':'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.3 Safari/605.1.15'})
soup = BeautifulSoup(response.text, 'html.parser')
articles = soup.select("div.rankingnews_box")

target_articles = {}

for index, item in enumerate(articles):
    article_title = item.select("ul.rankingnews_list a")[0].text
    article_press = item.select("strong.rankingnews_name")[0].text
    article_time = item.select("span.list_time")[0].text
 
    article = {}
    article['type'] = 'top1_comment'
    article['title'] = article_title
    article['press'] = article_press
    article['time'] = article_time
    
    target_articles[index] = article

targets = list()
for value in target_articles.values():
    targets.append(value)
df_artc_top_comm = pd.DataFrame(data=targets)
df_artc_top_comm

# page 1) #################################### home ########################################
@app.route('/')
def index():
    return render_template('index.html')

# page 2-1) #################################### Daum News - 정치 30 page ########################################
@app.route('/politics')
def politics():
    context = news.loc[news['type']=='politics', ['title','txt','press','time','link']]
    return render_template('politics.html', context=context.to_dict(orient='index'))
# page 2-2) #################################### Daum News - 경제 ########################################
@app.route('/economics')
def economics():
    context = news.loc[news['type']=='economic', ['title','txt','press','time','link']]
    return render_template('economics.html', context=context.to_dict(orient='index'))

# page 2-3) #################################### Daum News - 사회 ########################################
@app.route('/social')
def social():
    context = news.loc[news['type']=='society', ['title','txt','press','time','link']]
    return render_template('social.html', context=context.to_dict(orient='index'))
# page 2-4) #################################### Daum News - IT / 과학 ########################################
@app.route('/it_science')
def it_science():
    context = news.loc[news['type']=='digital', ['title','txt','press','time','link']]
    return render_template('it_science.html', context=context.to_dict(orient='index'))    

# page 3-1) #################################### save ########################################

@app.route('/save')

def save():
    filename = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    writer = pd.ExcelWriter("log-"+filename+".xlsx", engine='xlsxwriter')

    # Write each dataframe to a different worksheet.
    news.to_excel(writer, sheet_name='All_News')
    df_artc_top_view.to_excel(writer, sheet_name='Top_View_News')
    df_artc_top_comm.to_excel(writer, sheet_name='Top_Comments_News')
    writer.close()
    message = "오늘의 모든 4개 분야 뉴스기사, 조회수가 많은 뉴스기사, 댓글수가 많은 뉴스기사 데이터가 엑셀로 다운로드 완료 되었습니다."

    return message

#4) #################################### Data Analysis ########################################

@app.route('/analysis')
def analysis():
    # analysis 0 - 분석 개괄 공지 문구
    
    # 지난 시간 계산
    now = datetime.now()
    start = datetime(now.year, now.month, now.day)
    diff = now - start
    diff
    total_seconds = diff.total_seconds()
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    result_str = f"{hours}시간 {minutes}분"
    result_str
    # 공지 문구 제작
    result_str = f"{hours}시간 {minutes}분"
    title_cnt = news['title'].count()
    press_cnt = pd.DataFrame(news['press'].unique())[0].count()
    politics_count = news[news['type'] == 'politics']['title'].count()
    economic_count = news[news['type'] == 'economic']['title'].count()
    society_count = news[news['type'] == 'society']['title'].count()
    digital_count = news[news['type'] == 'digital']['title'].count()
    notice = f"기사 수집은 하루가 지나면 초기화 됩니다.\n오늘, 현재까지 {result_str} 동안 수집된 기사는 총 {title_cnt}개, {press_cnt}개의 언론사가 보도하였습니다.\n각 분야 별로는 정치 {politics_count}개, 경제 {economic_count}개, 사회 {society_count}개, IT/과학 {digital_count}개 기사가 수집되었습니다."
    notice

    # # analysis 1 - 섹션별 기사 수 그래프
    # type_dict = {'Politics': politics_count,
    #             'Economics': economic_count,
    #             'Society': society_count,
    #             'IT/Science': digital_count}
    # type_df = pd.DataFrame.from_dict(data=type_dict, orient='index', columns=['count'])
    # sns.set_style("whitegrid")
    # sns.barplot(x=type_df['count'], y=type_df.index, palette=["#b2df8a", "#a6cee3", "#fb9a99", "#fdbf6f"] )
    # sns.despine(left=True, bottom=True)
    # plt.savefig('static/images/section_cnt.jpg')

    # analysis 2 - express top3 view and comments title
    dfi.export(df_artc_top_view[['title']].rename(columns={'title':'오늘의 조회 수, Top3'})[:3].style.hide(),'static/images/top3_view.jpg')
    dfi.export(df_artc_top_comm[['title']].rename(columns={'title':'오늘의 댓글 수, Top3'})[:3].style.hide(),'static/images/top3_comm.jpg')

    # analysis 3 - express keywords count on the wordcloud, all fields and each section of news
# analysis 3 - express keywords count on the wordcloud, all fields and each section of news
    pol = news[news['type']=='politics'][:150]
    eco = news[news['type']=='economic'][:150]
    soc = news[news['type']=='society'][:150]
    dig = news[news['type']=='digital'][:150]

    news = pd.concat([pol,eco,soc,dig]).reset_index(drop=True)

    news_types = ['all', 'politics', 'economic', 'society', 'digital']
    colormaps = ['Set3','Blues', 'Greens', 'Oranges', 'Purples']

    for i, news_type in enumerate(news_types):
        # Load data
        if news_type == 'all':
            title_origin = news['txt'] + news['title']
        else:
            title_origin =  news[news['type']==news_type]['title'] + news[news['type']==news_type]['txt']

        titles = list(title_origin)
        ana_text = " ".join(titles)

        # Nouns extraction
        kkma = Kkma()
        noun_list = kkma.nouns(ana_text)
        noun_list = [word for word in noun_list if len(word) > 2]
        counts = Counter(noun_list)
        target_words = counts.most_common(20)

        # WordCloud generation
        wc_kwargs = {"font_path":"Library/Fonts/NanumGothic.ttf", "max_font_size":60,'background_color':'black'}
        wc_kwargs['colormap'] = colormaps[i]

        wc = WordCloud(**wc_kwargs)
        cloud = wc.generate_from_frequencies(dict(target_words))

        # Save image
        filename = f"wc_{news_type}.jpg"
        filepath = 'static/images/'+filename
        cloud.to_file(filepath) 

        return render_template('board.html', notice = notice)
    
if __name__ == '__main__':
    app.run('0.0.0.0', port=9000, debug=True)   
# -*- coding:utf-8 -*-
#こんな風にして近代ライブラリーからタイトルとpidのリストを作る
# python kindai_list.py 百科事典

import sys
import re
import os
import requests
from bs4 import BeautifulSoup


def get_soup_page(url):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}
    res = requests.get(url, headers=headers) 
    content = res.text  # 情報ページ内容を取得
    soup = BeautifulSoup(content)  # 情報ページのsoupを取得
    return soup

def get_bookinfo(soup):
    strings = ""
    r_pid = re.compile(r'/info:ndljp/pid/([0-9]+)')

    items = soup.findAll('td', attrs = {'class': 'item-info'})
    for item in items:
        titlep = item.find('p', attrs = {'class': 'titlep'})
        #pid取得
        pid_title = titlep.find('a', attrs = {'class': 'item-link'})
        m_pid = r_pid.search(dict(pid_title.attrs)['href'])
        pid = m_pid.group(1)
        #タイトル取得
        title = pid_title.get_text()
        #著者、出版社取得
        #<p class="details">
        details = item.find('p', attrs = {'class': 'details'})
        details = details.get_text().strip()

        strings = strings + pid + '\t' + title + '\t' + details +'\n'
    return strings


def get_hits_num(soup):
    tableheadercontent = soup.find('div', attrs = {'class': 'tableheadercontent tableheadercontent-left'}) 
    hits_num_strings = tableheadercontent.find('p').get_text()
    hits_num_strings = str(hits_num_strings)
    r_hits = re.compile('検索結果（([0-9]+)')
    m_hits = r_hits.search(hits_num_strings)
    #print type(hits_num_strings), type(m_hits)
    hits = m_hits.group(1)
    return hits 

main():
    search_keyword = sys.argv[1]  #引数を検索キーワードにする
    #search_keyword = "これは"
    url = "http://kindai.ndl.go.jp/search/searchResult?title=%s&reshowFlg=1&detailSearchTypeNo=K&rows=200" % search_keyword
    soup = get_soup_page(url)
    hits_num = int(get_hits_num(soup))
    #print hits_num
    #200未満ならここで終わり
    print get_bookinfo(soup)
    #200以上ならこのループへ
    for page in range(2, hits_num/200 + 1):
        url = "http://kindai.ndl.go.jp/search/searchResult?title=%s&pageNo=%s&reshowFlg=1&detailSearchTypeNo=K&rows=200" % (search_keyword, page)
        soup = get_soup_page(url)
        print get_bookinfo(soup)


if __name__ == '__main__':
    main()

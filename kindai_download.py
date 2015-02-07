# -*- coding:utf-8 -*-

#以下にダウンロードするpidコードのリストを並べる
pid_list = '''\
1444386
992868
1879853
1920697
1764781
991742
'''

import time
import re
import os
import requests
from bs4 import BeautifulSoup
from PyPDF2 import PdfFileMerger, PdfFileWriter, PdfFileReader


#リストinput_filesで渡されたpdfファイルたちを一つにまとめる
def pdf_merge(input_files, output_file):
    merger = PdfFileMerger()

    for f in input_files:
    # expect filename as "*.pdf"
        if f[-4:] != ".pdf":
            print "skipped file: ", f
            continue
        else:
            input = open(f, 'rb')
            merger.append(input)
            print "merged file: ", f
            #マージしたファイルは削除
            os.remove(f)
    output = open(output_file, "wb")
    merger.write(output)


#pdf_fileにmokujiの情報を使ってブックマーク付け
def add_bookmark(input_file, output_file, mokuji):
        #pdfを用意
        output = PdfFileWriter()
        input = PdfFileReader(open(input_file, 'rb'))
        num_pages = input.getNumPages()
        for i in xrange(0, num_pages):
            output.addPage(input.getPage(i))
        #mokujiの情報を使ってブックマーク付け
        for now_bookmark in mokuji:
            print now_bookmark[0], now_bookmark[1]
            bk_title = now_bookmark[0]
            page_num = int(now_bookmark[1])-1
            output.addBookmark(bk_title, page_num)
        #ファイルを保存
        d = open(output_file, "wb")
        output.write(d)
        d.close()


#pidを与えられると最大ページ数とタイトルと（あれば目次）を返す
def get_info(now_pid):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}

    now_url = "http://kindai.ndl.go.jp/info:ndljp/pid/" + now_pid  ##情報ページのURL
    res = requests.get(now_url, headers=headers)  #ページ内容を取得
    
    soup = BeautifulSoup(res.text)

    ##最大ページ数抜き出し
    #<input type="hidden" name="lastContentNo" id="lastContentNo" value="107"/>
    lastContentField = soup.find('input', attrs={'name':'lastContentNo'}) 
    now_max = dict(lastContentField.attrs)['value']

    ##タイトル抜き出し
    #<title>近代デジタルライブラリー - 書物語辞典</title>
    titleField = str(soup.title)
    r = re.compile(r'<title>近代デジタルライブラリー - ([^<]+)</title>')
    m = r.search(titleField)
    now_title = m.group(1)

    #目次を取り出す
    mokuji =[]

    #<ul class="ndltree">
    try:
        ndltree = soup.find('ul', attrs={'class':'ndltree'}) 
        #<a href="/info:ndljp/pid/1079076/3?tocOpened=1" class="ndltree-item ndltree-label" title="標題">
        items = ndltree.findAll('a', attrs={'class':'ndltree-item ndltree-label'})

        recom = re.compile(r'/info:ndljp/pid/[0-9]+/([0-9]+)')

        for item in items[1:]:
            #print item
            nowbk_title = (item.string).split('/')[0]  # 官版書籍解題略/172p
            
            #print dict(item.attrs)['href']  # attrsはタプルのリストなので辞書経由でアクセスが便利
            #href="/info:ndljp/pid/1079076/257?tocOpened=1　から257を取り出す
            m2 = recom.search(dict(item.attrs)['href'])
            now_page = m2.group(1)
            mokuji.append( (nowbk_title, now_page) )
    except:
        pass

    return (now_title, now_max, mokuji)


def pages_download(now_pid, start_page, end_page):
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}
    download_url='http://kindai.ndl.go.jp/view/pdf/digidepo_'+now_pid+'.pdf?pdfOutputRangeType=R&pdfPageSize=&pdfOutputRanges='
    now_url = download_url+str(start_page)+'-'+str(end_page)
    now_filename = now_pid + '--' + str(start_page) + '.pdf'
    print 'Fetching', now_url
    #ファイルを取得
    r = requests.get(now_url, headers=headers)
    #ファイル名now_filenameで保存
    f = open(now_filename, "wb")
    f.write(r.content)
    return now_filename


def book_download(now_pid, now_max, page_size=20):
    #now_pidの本について
    #page_size頁ごとに分割してダウンロードし
    #分割ファイルのリストを返す
    sub_file_list = []
    #20頁ごとに区切ってダウンロード
    for now_start_page in range (1, int(now_max), page_size):
        #ダウンロード
        now_end_page = int(now_start_page) + page_size -1
        if now_end_page > int(now_max):
            now_filename = pages_download(now_pid, now_start_page, now_max)
        else:
            now_filename = pages_download(now_pid, now_start_page, now_end_page)
        sub_file_list.append(now_filename)
        time.sleep(20) #20秒スリープ
    return sub_file_list



#メインループのはじまり
main():
    for now_pid in pid_list.split():
        #now_pidの１冊のダウンロード

        #情報ページでタイトルと最大数と目次を取得
        (now_title, now_max, mokuji) = get_info(now_pid)

        print 'Downloading pid=', now_pid, now_title, '---ページ総数:', now_max

        #page_size毎に分割ダウンロード
        sub_file_list = book_download (now_pid, now_max, page_size=20)

        #pdfファイルを連結
        pdf_merge(sub_file_list, now_pid + '.pdf')

        if mokuji:
            #目次があればブックマークつける
            add_bookmark(now_pid + '.pdf', now_title + '.pdf', mokuji)
            os.remove(now_pid + '.pdf')
        else:
            #目次がない場合はpdfファイル名を書名に変えて終わり
            os.rename(now_pid + '.pdf' , now_title + '.pdf')   


if __name__ == '__main__':
    main()

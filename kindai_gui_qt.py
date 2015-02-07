# -*- coding:utf-8 -*-
import re
import os
import requests
from bs4 import BeautifulSoup
import time
from PyPDF2 import PdfFileMerger, PdfFileWriter, PdfFileReader
from PyQt4 import QtGui, QtCore
from clint.textui import progress


# デフォルトの文字コードの変更
import sys
# sysモジュールをリロードする
reload(sys)
# デフォルトの文字コードを変更する．
sys.setdefaultencoding('utf-8')


class my_window(QtGui.QWidget):

    def __init__(self):
        super(my_window, self).__init__()
        self.initUi()

    def initUi(self):
        self.btnExec = QtGui.QPushButton(u'検索', self)
        self.btnExec.move(420, 15)
        self.btnExec.clicked.connect(self.doExecute)

        self.btnClear = QtGui.QPushButton(u'クリア', self)
        self.btnClear.move(480, 15)
        self.btnClear.clicked.connect(self.doClear)

        #検索用入力フォーム
        self.txtInput = QtGui.QLineEdit(self)
        self.txtInput.setGeometry(0, 0, 400, 25)
        self.txtInput.move(20, 15)

        # 検索結果出力フォーム
        self.txtLeft = QtGui.QTextEdit(self)
        self.txtLeft.setGeometry(0, 0, 650, 200)
        self.txtLeft.move(20, 50)
        self.txtLeft.setLineWrapMode(QtGui.QTextEdit.NoWrap)

        #ダウンロード 
        self.btnDownload = QtGui.QPushButton(u'ダウンロード', self)
        self.btnDownload.move(20, 255)
        self.btnDownload.clicked.connect(self.doDownload)

        #ダウンロード先指定
        self.btnDownload = QtGui.QPushButton(u'ダウンロード先', self)
        self.btnDownload.move(130, 255)
        self.btnDownload.clicked.connect(self.open_folder)

        self.dl_place = QtGui.QLabel(os.getcwd(), self)
        self.dl_place.setGeometry(0, 0, 400, 20)
        self.dl_place.move(270, 260)

        #プログレスバーはここに
        self.dl_book = QtGui.QLabel('', self)
        self.dl_book.setGeometry(0, 0, 630, 20)
        self.dl_book.move(50, 300)

        self.dl_file = QtGui.QLabel('', self)
        self.dl_file.setGeometry(0, 0, 300, 20)
        self.dl_file.move(50, 325)

        self.pbar = QtGui.QProgressBar(self)
        self.pbar.setRange(0, 100)
        self.pbar.setGeometry(0, 0, 600, 20)
        self.pbar.move(50, 350)

        self.dl_speed = QtGui.QLabel('', self)
        self.dl_speed.setGeometry(0, 0, 300, 20)
        self.dl_speed.move(350, 375)
        self.dl_speed.setAlignment(QtCore.Qt.AlignRight)

        #全体の大きさとタイトル
        self.setGeometry(200, 200, 690, 400)
        self.setWindowTitle('Kindai Downloader')
        self.show()
        self.raise_()

    def doExecute(self, value):
        self.txtLeft.setText(keyword_search(self.txtInput.text()))

    def doClear(self, value):
        self.txtLeft.clear()

    def open_folder(self):
        foldername = QtGui.QFileDialog.getExistingDirectory(self, 'Open Directory', os.path.expanduser('~') + '/Desktop')
        #print foldername
        self.dl_place.setText(foldername)
        os.chdir(foldername)

    def doDownload(self, value):
        search_result = self.txtLeft.toPlainText()
        search_result = unicode(search_result).strip()
        download_lines = search_result.split('\n')
        excute_download(download_lines)
        
        finish()
        
        # ex = EndMessage()
        # ex.show()
        # ex.raise_()
        self.txtLeft.clear()

def finish():
    global now_window
    now_window.dl_book.setText(u"リストにあった書物のダウンロードを終了しました")
    now_window.dl_file.setText('')
    now_window.dl_speed.setText('')
    now_window.pbar.setValue(0)





class download_thread():
    def __init__(self, url, file_name):
        self.url = url
        self.file_name = file_name

    def run(self):
        global app, now_window
        start = time.clock()
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}
        r = requests.get(self.url, headers=headers, stream=True)
        with open(self.file_name, 'wb') as f:
            total_length = int(r.headers.get('content-length'))
            if total_length is None:  #no content length header
                f.write(r.content)
            else:
                dl = 0
                max = 100
                for chunk in r.iter_content(chunk_size=1024):
                    dl += len(chunk)
                    f.write(chunk)
                    f.flush()
                    progress_ratio = int(max*dl / total_length)
                    progress_speed = str(dl//(time.clock() - start))
                    self.progress_state(self.file_name, progress_ratio, progress_speed)
        now_window.dl_file.setText(self.file_name + 'is finished.')
        app.processEvents()


    def progress_state(self, dl_file, progress_ratio, progress_speed):
        global app, now_window
        now_window.dl_file.setText('loading file: ' + dl_file)
        now_window.pbar.setValue(progress_ratio)
        now_window.dl_speed.setText('loading speed: ' + str(progress_speed) + 'bps')
        app.processEvents()


def waiting():
        global app, now_window
        now_window.dl_file.setText('waiting... in order to reduce server load')
        for step in range(100):
            now_window.pbar.setValue(step)
            app.processEvents()
            time.sleep(20.0/100)
        now_window.dl_file.setText('')



class kindai(object):
    #みんなで使う変数
    #pdfの最大ダウンロード頁数 pdf_dowonload_maxnum
    #どの本かを示すpid

    def get_mokuji(self, soup):
        mokuji = []
        try:
            ndltree = soup.find('ul', attrs = {'class': 'ndltree'})
            items = ndltree.findAll('a', attrs = {'class': 'ndltree-item ndltree-label'})
            recom = re.compile(r'/info:ndljp/pid/[0-9]+/([0-9]+)')
            for item in items[1:]:
                #print item
                nowbk_title = (item.string).split('/')[0]  # 官版書籍解題略/172p
                #print dict(item.attrs)['href']  # attrsはタプルのリストなので辞書経由でアクセスが便利
                #href="/info:ndljp/pid/1079076/257?tocOpened=1　から257を取り出す
                m2 = recom.search(dict(item.attrs)['href'])
                now_page = m2.group(1)
                mokuji.append((nowbk_title, now_page))
        except:
            pass
        return mokuji

    def get_soup_infopage(self, now_pid):
        headers = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11'}

        self.infopage_url = "http://kindai.ndl.go.jp/info:ndljp/pid/" + str(now_pid)  ##情報ページのURL
        res = requests.get(self.infopage_url, headers=headers) 
        content = res.text  #情報ページ内容を取得
        soup = BeautifulSoup(content)  #情報ページのsoupを取得
        return soup


    def __init__(self, pid):
        self.pdf_dowonload_maxnum = 50
        self.pid = pid

        soup = self.get_soup_infopage(pid)

        ##最大ページ数抜き出し
        #<input type="hidden" name="lastContentNo" id="lastContentNo" value="107"/>
        lastContentField = soup.find('input', attrs={'name':'lastContentNo'})
        self.maxpage = dict(lastContentField.attrs)['value']

        ##タイトル抜き出し
        #<title>近代デジタルライブラリー - 書物語辞典</title>
        titleField = soup.title.encode('utf-8')
        r = re.compile(r'<title>近代デジタルライブラリー - ([^<]+)</title>')
        m = r.search(titleField)
        self.title = m.group(1)

        ##目次抜き出し
        self.mokuji = self.get_mokuji(soup)


#リストinput_filesで渡されたpdfファイルたちを一つにまとめる
    def pdf_merge(self, input_files, output_file):
        global app, now_window
        now_window.dl_file.setText('Now Merging...')

        merger = PdfFileMerger()

        l = len (input_files)
        for i, f in enumerate(input_files):
            now_window.pbar.setValue(100.0*i/l)
        # expect filename as "*.pdf"
            if f[-4:] != ".pdf":
                print "skipped file: ", f
                continue
            else:
                input = open(f, 'rb')
                merger.append(input)
                #print "merged file: ", f
                now_window.dl_speed.setText('merged file: ' + f)
                #マージしたファイルは削除
                os.remove(f)
            app.processEvents()
        output = open(output_file, "wb")
        merger.write(output)



    #pdf_fileにself.mokujiの情報を使ってブックマーク付け
    def add_bookmark(self, input_file, output_file):
            #pdfを用意
            global app, now_window
            now_window.dl_file.setText('Now Bookmarking...')
            app.processEvents()

            output = PdfFileWriter()
            input = PdfFileReader(open(input_file, 'rb'))
            num_pages = input.getNumPages()
            for i in xrange(0, num_pages):
                output.addPage(input.getPage(i))
            #self.mokujiの情報を使ってブックマーク付け
            l = len (self.mokuji)
            for i, now_bookmark in enumerate(self.mokuji):
                bk_title = now_bookmark[0]
                page_num = int(now_bookmark[1])-1
                now_window.dl_file.setText('Now Bookmarking...' + bk_title +':'+ str(page_num))
                output.addBookmark(bk_title, page_num)
                now_window.pbar.setValue(100.0*i/l)
                app.processEvents()
            #ファイルを保存
            d = open(output_file, "wb")
            output.write(d)
            d.close()
            now_window.dl_file.setText('')
            app.processEvents()

    def pdf_pages_download(self, start_page, end_page):
        global app, now_window

        download_url='http://kindai.ndl.go.jp/view/pdf/digidepo_'+str(self.pid)+'.pdf?pdfOutputRangeType=R&pdfPageSize=&pdfOutputRanges='
        now_url = download_url + str(start_page) + '-' + str(end_page)
        now_filename = str(self.pid) + '--' + str(start_page) + '--' + str(end_page) +'.pdf'
        now_window.dl_file.setText('loading file: ' + now_filename)
        app.processEvents()
        #ファイルを取得
        thread = download_thread(now_url, now_filename)
        thread.run()

        now_window.dl_file.setText('Download finish !!' + now_filename)
        app.processEvents()
        return now_filename


    def pdf_bookparts_download(self):
        #self.pidの本について
        #self.pdf_dowonload_maxnum頁ごとに分割してダウンロードし
        #分割ファイルのリストを返す
        sub_file_list = []
        #20頁ごとに区切ってダウンロード
        for now_start_page in range (1, int(self.maxpage), self.pdf_dowonload_maxnum):
            #ダウンロード
            now_end_page = int(now_start_page) + int(self.pdf_dowonload_maxnum) -1
            if now_end_page > int(self.maxpage):
                now_filename = self.pdf_pages_download(now_start_page, self.maxpage)
            else:
                now_filename = self.pdf_pages_download(now_start_page, now_end_page)
            sub_file_list.append(now_filename)

            waiting() #20秒スリープ 

        return sub_file_list


    def pdf_download(self):
        global app, now_window
        now_window.dl_book.setText(unicode(self.title) + u'  ---全' + self.maxpage + u'頁')
        now_window.dl_file.setText('Fetching Information...')
        app.processEvents()

        #print 'Downloading pid=', self.pid, self.title, '---ページ総数:', self.maxpage

        #self.pdf_dowonload_maxnum毎に分割ダウンロード
        sub_file_list = self.pdf_bookparts_download()

        temp_pdf = str(self.pid) + '.pdf'

        #pdfファイルを連結
        self.pdf_merge(sub_file_list, temp_pdf)

        if self.mokuji:
            #目次があればブックマークつける
            self.add_bookmark(temp_pdf, self.title + '.pdf')
            os.remove(temp_pdf)
        else:
            #目次がない場合はpdfファイル名を書名に変えて終わり
            os.rename(temp_pdf , self.title + '.pdf') 


def excute_download(my_list):
    for line in my_list:
        now_pid = line[:-1].split('\t')[0]
        nowbook = kindai(now_pid)
        nowbook.pdf_download()



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
    # hits_num_strings = str(hits_num_strings)
    hits_num_strings = hits_num_strings.encode('utf-8')
    r_hits = re.compile('検索結果（([0-9]+)')
    m_hits = r_hits.search(hits_num_strings)
    #print type(hits_num_strings), type(m_hits)
    hits = m_hits.group(1)
    return hits 


def keyword_search(search_keyword):
    #search_keyword = "これは"
    url = "http://kindai.ndl.go.jp/search/searchResult?title=%s&reshowFlg=1&detailSearchTypeNo=K&rows=200" % search_keyword
    soup = get_soup_page(url)
    hits_num = int(get_hits_num(soup))
    #print hits_num
    #200未満ならここで終わり
    my_list = get_bookinfo(soup)
    #200以上ならこのループへ
    for page in range(2, hits_num/200 + 1):
        url = "http://kindai.ndl.go.jp/search/searchResult?title=%s&pageNo=%s&reshowFlg=1&detailSearchTypeNo=K&rows=200" % (search_keyword, page)
        soup = get_soup_page(url)
        my_list = my_list + get_bookinfo(soup)
    return my_list


def main():
    global app, now_window
    app = QtGui.QApplication(sys.argv)
    now_window = my_window()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()

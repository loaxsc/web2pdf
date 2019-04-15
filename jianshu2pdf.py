#!/usr/bin/python3
# vim: fdm=marker
from selenium.webdriver.firefox.options import Options
from selenium import webdriver
from bs4 import BeautifulSoup, Tag
import urllib.request, http.cookiejar, execjs
import sys, os, re, time, subprocess

# Funcitons {{{
def pre_elem(elem):
    parent_id = id(elem.parent)
    for pre_node in elem.previous_siblings:
        if id(pre_node) == parent_id:
            return None
        if 'Tag' in str(pre_node.__class__):
            return pre_node

def next_elem(elem):
    next_parent_id = id(elem.parent.next_sibling)
    for next_node in elem.next_siblings:
        if id(next_node) == next_parent_id:
            return None
        if 'Tag' in str(next_node.__class__):
            return next_node

def idx_of_elem(elem):
    """ Return the position of element in the contents of its parent """
    p_id = id(elem.parent)
    i = 0
    while id(elem.previous) != p_id:
        elem = elem.previousSibling
        i += 1
    return i # }}}

title = '萬維鋼講相對論'
articles = []
with open('articles.txt') as f:
    txt = f.read().strip().split('\n')
for line in txt:
    articles.append(dict(title=line.split(',')[0], url=line.split(',')[1]))

opener = urllib.request.build_opener()
des = """\
<?xml version='1.0' encoding='utf-8'?>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
  <meta content="text/html; charset=utf-8" http-equiv="content-type" />
  <link href="web2pdf.css" rel="stylesheet" type="text/css"/>
  <title>{title}</title>
</head>
<body>{content}
  <script src="http://cdnjs.cloudflare.com/ajax/libs/Han/3.3.0/han.min.js"></script>
  <script type="text/javascript">Han(document.body).initCond().renderHWS()</script>
</body>
</html>
"""
content = ''
opener.addheaders = [('User-Agent','Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:65.0) Gecko/20100101 Firefox/65.0')]

for  article in articles:
    print('processing {}'.format(article['title']))
    html = opener.open(article['url']).read().decode('utf-8','ignore')
    soup = BeautifulSoup(html,'lxml')

    div = soup.find('div','show-content-free')
    div.insert(0,soup.h1)

    # figure # {{{
    elems = div.find_all('img',attrs={'data-original-src':True})
    if len(elems) > 0:
        for elem in elems:
            src = elem['data-original-src']
            attrs = [ attr for attr in elem.attrs ]
            for attr in attrs:
                del elem[attr]
            elem['src'] = 'http:' + src
            elem.parent.name = 'figure'
            elem.parent.parent.parent.replace_with(elem.parent) # }}}

    brs = div.find_all('br')
    for br in brs:
        br.extract()

    # footnote {{{
    elems = [ elem.parent for elem in div.find_all(text=re.compile(r'^\[\d+\]')) ]
    if len(elems) > 0:
        for elem in elems:
            elem['class'] = 'fnote' # }}}

    #nl {{{
    re_nl = re.compile(r'^\s*(第[一二三四五六七八九]，|\d+[）\.])')
    elems = [ e.parent for e in soup.find_all(text=re_nl) if e.parent.name == 'p' ]
    lst_nl = []
    for elem in elems:
        if next_elem(elem) and re.match(re_nl, next_elem(elem).text):
            lst_nl.append(elem)
            continue
        if pre_elem(elem) and re.match(re_nl, pre_elem(elem).text):
            lst_nl.append(elem)
            div_li = soup.new_tag('div')
            div_li['class'] = 'nl'
            lst_nl[0].insert_before(div_li)
            for e in lst_nl:
                div_li.append(e)
            lst_nl = [] # }}}

    #ul {{{
    re_ul = re.compile(r'^\s*[\*•]')
    elems = [ e.parent for e in soup.find_all(text=re_ul) if e.parent.name == 'p' ]
    lst_ul = []
    for elem in elems:
        if next_elem(elem) and re.match(re_ul, next_elem(elem).text):
            lst_ul.append(elem)
            continue
        if pre_elem(elem) and re.match(re_ul, pre_elem(elem).text):
            lst_ul.append(elem)
            div_li = soup.new_tag('div')
            div_li['class'] = 'ul'
            lst_ul[0].insert_before(div_li)
            for e in lst_ul:
                div_li.append(e)
            lst_ul = [] # }}}

    #H2 {{{
    elems = div.find_all('p')
    for elem in elems:
        if re.match(r'\s*\d\.|参考文献|注释|^\s*\| .+$',elem.text) and 'show-content-free' in elem.parent['class']:
            span = soup.new_tag('span')
            span.insert(0,elem.string)
            elem.insert(0,span)
            elem.name = 'h2' # }}}

    content += re.sub(r'(?s)<div .+?>(.+)</div>',r'\1',str(div),1).strip() + '\n'


content = re.sub(r'“',r'「',content)
content = re.sub(r'”',r'」',content)

with open('/tmp/prince.input.html','w') as f:
    f.write(des.format(title=title,content=content))

options = Options()
profile = webdriver.FirefoxProfile()
profile.set_preference('permissions.default.image', 2)
profile.set_preference('dom.ipc.plugins.enabled.libflashplayer.so', 'false')

ff = webdriver.Firefox(options=options, firefox_profile=profile)
ff.get('file:///tmp/prince.input.html')

while True:
    time.sleep(0.1)
    if  ff.execute_script('return document.readyState') == 'complete':
        break

soup = BeautifulSoup(ff.page_source,'lxml')
ff.quit()

scripts = soup.find_all('script')
for elem in scripts:
    elem.extract()

with open('output.html','w') as f:
    f.write(soup.__str__())

subprocess.call(['prince', 'output.html'])
os.remove('output.html')
os.remove('geckodriver.log')

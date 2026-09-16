# -*- coding: utf-8 -*-
import zipfile, sys
from lxml import etree
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
p = r"D:/STM32_Project/docs/串口数据控制测试_接口文档.docx"
with zipfile.ZipFile(p) as z:
    root = etree.fromstring(z.read('word/document.xml'))
body = root.find(W+'body')
ti = 0
for i, e in enumerate(body):
    tag = etree.QName(e).localname
    if tag == 'p':
        st = e.find(W+'pPr/'+W+'pStyle')
        val = st.get(W+'val') if st is not None else ''
        txt = ''.join(t.text or '' for t in e.iter(W+'t')).strip()
        if txt:
            mark = 'H' if val in ('1','2','3','4','Heading1','heading1','00001e','000020','000021') else ' '
            print(f"{i:4d} [{val:>8}] {mark} {txt[:70]}")
    elif tag == 'tbl':
        ti += 1
        rows = e.findall(W+'tr')
        first = ''.join(t.text or '' for t in rows[0].iter(W+'t')).strip()[:60]
        print(f"{i:4d} <TBL{ti:02d}> rows={len(rows)} | {first}")
print("TABLES:", ti)

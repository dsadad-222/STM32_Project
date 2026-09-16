# -*- coding: utf-8 -*-
import zipfile
from lxml import etree
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
p = r"D:/STM32_Project/docs/串口数据控制测试_接口文档.docx"
with zipfile.ZipFile(p) as z:
    root = etree.fromstring(z.read('word/document.xml'))
body = root.find(W+'body')
els = list(body)

def ptext(i):
    return ''.join(t.text or '' for t in els[i].iter(W+'t'))

def cells(tbl):
    out=[]
    for tr in tbl.findall(W+'tr'):
        out.append([''.join(t.text or '' for t in tc.iter(W+'t')) for tc in tr.findall(W+'tc')])
    return out

for i in [36,105,107,110,123,126,128,130]:
    print(f"--- TBL@{i} ---")
    for r in cells(els[i]):
        print(" | ".join(r))
print()
for i in [94,96,98,104,108,113,114,115,116,117,118,119,120,121,124,127,129,131,132,134,135,137,156,159,168,173,175,177,184,185,186,192,205,207,209]:
    print(f"P{i}: {ptext(i)}")

# -*- coding: utf-8 -*-
"""打印指定段落范围与指定表格的全部文本（用于精确改文档）。"""
import sys
import zipfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
q = lambda t: '{%s}%s' % (W, t)

path = r'D:/STM32_Project/docs/串口数据控制测试_接口文档.docx'
z = zipfile.ZipFile(path)
root = etree.fromstring(z.read('word/document.xml'))
body = root.find(q('body'))

paras = []
tbls = []
for ch in body:
    if ch.tag == q('p'):
        paras.append(ch)
    elif ch.tag == q('tbl'):
        tbls.append(ch)

def ptext(p):
    return ''.join(t.text or '' for t in p.iter(q('t')))

a, b = int(sys.argv[1]), int(sys.argv[2])
print('=' * 30, f'paragraphs {a}..{b}', '=' * 30)
for i in range(a, min(b, len(paras))):
    print(f'--- P{i}: {ptext(paras[i])}')

print()
print('=' * 30, 'tables', '=' * 30)
for ti in [int(x) for x in sys.argv[3:]]:
    t = tbls[ti]
    print(f'### TBL#{ti} rows={len(t.findall(q("tr")))}  cols={len(t.findall(q("tblGrid")+"/"+q("gridCol")))}')
    for ri, tr in enumerate(t.findall(q('tr'))):
        cells = [' '.join(''.join(x.text or '' for x in tc.iter(q('t'))).split()) for tc in tr.findall(q('tc'))]
        print(f'   r{ri}: {cells}')

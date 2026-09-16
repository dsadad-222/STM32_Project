# -*- coding: utf-8 -*-
"""把接口文档的结构 dump 出来：段落样式 + 文本、表格清单 + 表格首行，方便定位改哪里。"""
import sys
import zipfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
q = lambda t: '{%s}%s' % (W, t)

path = sys.argv[1] if len(sys.argv) > 1 else r'D:/STM32_Project/docs/串口数据控制测试_接口文档.docx'
z = zipfile.ZipFile(path)
root = etree.fromstring(z.read('word/document.xml'))
body = root.find(q('body'))

STYLE_MAP = {
    '00001e': 'H1', '000020': 'H3', '000021': 'H4', '000026': 'Subtitle',
}

idx = 0
tbl_no = 0
for ch in body:
    if ch.tag == q('p'):
        st = ch.find(q('pPr') + '/' + q('pStyle'))
        stid = st.get(q('val')) if st is not None else ''
        txt = ''.join(t.text or '' for t in ch.iter(q('t'))).strip()
        mark = STYLE_MAP.get(stid, '')
        if mark or (txt and len(txt) < 60):
            print(f'P{idx:4d} {mark:8s} {txt[:70]}')
        idx += 1
    elif ch.tag == q('tbl'):
        rows = ch.findall(q('tr'))
        first = ''
        firstrow = []
        for tc in rows[0].findall(q('tc')) if rows else []:
            firstrow.append(''.join(t.text or '' for t in tc.iter(q('t'))).strip()[:26])
        second = ''
        if len(rows) > 1:
            cs = rows[1].findall(q('tc'))
            second = ' | '.join(''.join(t.text or '' for t in tc.iter(q('t'))).strip()[:30] for tc in cs)
        ncols = len(ch.findall(q('tblGrid') + '/' + q('gridCol'))) if ch.find(q('tblGrid')) is not None else 0
        print(f'  TBL#{tbl_no:02d} rows={len(rows)} cols={ncols} r0=[{", ".join(firstrow)}] r1=[{second[:60]}]')
        tbl_no += 1

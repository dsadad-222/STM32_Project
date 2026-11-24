# -*- coding: utf-8 -*-
"""回读校验：把新文档的结构与关键内容打出来核对。"""
import zipfile
from lxml import etree

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def q(t):
    return '{%s}%s' % (W, t)


P = 'D:/STM32_Project/docs/片内片外FLASH读写_接口文档.docx'

with zipfile.ZipFile(P) as z:
    raw = z.read('word/document.xml')
    names = z.namelist()

print('zip 内文件数：', len(names))
print('document.xml 头 200 字节：')
print(raw[:200].decode('utf-8', 'replace'))
print()

root = etree.fromstring(raw)
print('root tag =', etree.QName(root).localname)
body = root.find(q('body'))
print('body is None?', body is None)
if body is None:
    raise SystemExit(1)


def txt(e):
    return ''.join(t.text or '' for t in e.iter(q('t')))


ti = 0
for i, el in enumerate(body):
    ln = etree.QName(el).localname
    if ln == 'tbl':
        ti += 1
        rows = el.findall(q('tr'))
        head = ' | '.join(txt(c) for c in rows[0].findall(q('tc')))
        print('[T%02d] body@%d rows=%d head=%r' % (ti, i, len(rows), head[:64]))
    elif ln == 'p':
        st = el.find(q('pPr') + '/' + q('pStyle'))
        s = st.get(q('val')) if st is not None else ''
        t = txt(el)
        if s in ('1', '3', '4'):
            print('  H%s @%d %s' % (s, i, t))
        elif s == 'ac':
            print('  AC @%d %s' % (i, t))
    else:
        print('  <%s> @%d' % (ln, i))

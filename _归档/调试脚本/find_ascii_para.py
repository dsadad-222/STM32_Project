# -*- coding: utf-8 -*-
"""定位接口文档里 ASCII 快捷命令那一段，看文本在 w:t 里是怎么切的。"""
import zipfile
from lxml import etree

DOC = r'D:\STM32_Project\docs\片内片外FLASH读写_接口文档.docx'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

z = zipfile.ZipFile(DOC)
root = etree.fromstring(z.read('word/document.xml'))
body = root.find(W + 'body')


def ptext(p):
    return ''.join(t.text or '' for t in p.iter(W + 't'))


hits = []
for i, el in enumerate(body):
    if etree.QName(el).localname != 'p':
        continue
    t = ptext(el)
    if '快捷命令' in t or 'S/C/P' in t or 'K 后跟温度值' in t:
        hits.append((i, t))

print('matched paragraphs:', len(hits))
print()

for i, t in hits:
    print('=' * 70)
    print('body[%d]  chars=%d' % (i, len(t)))
    print('TEXT:', t)
    el = body[i]
    print('--- runs ---')
    for j, r in enumerate(el.findall(W + 'r')):
        txt = ''.join(x.text or '' for x in r.iter(W + 't'))
        if txt:
            print('  run[%d]: %r' % (j, txt))
    print()

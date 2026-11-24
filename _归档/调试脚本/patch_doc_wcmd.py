# -*- coding: utf-8 -*-
"""在接口文档的 ASCII 快捷命令段落里补上 W 命令说明。

做法和 make_ch9_doc.py 一致：deepcopy 一个已有 run 改文字、addnext 插进去，
样式/编号/表格全部继承，不重建任何东西。
"""
import shutil
import zipfile
from copy import deepcopy

from lxml import etree

DOC = r'D:\STM32_Project\docs\片内片外FLASH读写_接口文档.docx'
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'

NEW_TEXT = ('W 后跟控制单元和十六进制数据可直接存进 Flash'
            '（如 W1DEADBEEF 存到片内、W2AABB 存到片外），'
            '回车或换行结束，效果等同发一条 0x07 协议帧；')

zf = zipfile.ZipFile(DOC)
names = zf.namelist()
parts = {n: zf.read(n) for n in names}
zf.close()

root = etree.fromstring(parts['word/document.xml'])
body = root.find(W + 'body')


def ptext(p):
    return ''.join(t.text or '' for t in p.iter(W + 't'))


target = None
for el in body:
    if etree.QName(el).localname != 'p':
        continue
    t = ptext(el)
    if '快捷命令' in t and 'S/C/P' in t:
        target = el
        break
assert target is not None, '没找到快捷命令段落'

anchor = None
for r in target.findall(W + 'r'):
    txt = ''.join(x.text or '' for x in r.iter(W + 't'))
    if '重新读回恢复' in txt:
        anchor = r
        break
assert anchor is not None, '没找到锚点 run'

new_run = deepcopy(anchor)
ts = new_run.findall(W + 't')
for extra in ts[1:]:
    new_run.remove(extra)
ts[0].text = NEW_TEXT
ts[0].set(XML_SPACE, 'preserve')
anchor.addnext(new_run)

parts['word/document.xml'] = etree.tostring(
    root, xml_declaration=True, encoding='UTF-8', standalone=True)

shutil.copy2(DOC, DOC + '.bak')
with zipfile.ZipFile(DOC, 'w', zipfile.ZIP_DEFLATED) as zo:
    for n in names:
        zo.writestr(n, parts[n])

print('patched ok')

# ---- 回读校验 ----
zf2 = zipfile.ZipFile(DOC)
r2 = etree.fromstring(zf2.read('word/document.xml'))
b2 = r2.find(W + 'body')
tbl = sum(1 for e in b2 if etree.QName(e).localname == 'tbl')
prg = sum(1 for e in b2 if etree.QName(e).localname == 'p')
for el in b2:
    if etree.QName(el).localname != 'p':
        continue
    t = ptext(el)
    if '快捷命令' in t and 'S/C/P' in t:
        print('tables=%d paragraphs=%d' % (tbl, prg))
        print('NEW TEXT:', t)
        break

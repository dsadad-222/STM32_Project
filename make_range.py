# -*- coding: utf-8 -*-
r"""保留 body 第 break_idx+1+a 到 break_idx+b 个子元素（其余正文删掉），用于二分定位。
用法: python make_range.py <in.docx> <out.docx> <a> <b>
"""
import sys
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def q(t):
    return f"{{{W}}}{t}"


src, dst, a, b = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
zin = zipfile.ZipFile(src)
root = etree.fromstring(zin.read("word/document.xml"))
body = root.find(q("body"))
children = list(body)

break_idx = None
for i, ch in enumerate(children):
    if ch.tag == q("p"):
        ppr = ch.find(q("pPr"))
        if ppr is not None and ppr.find(q("sectPr")) is not None:
            break_idx = i
final = None
for ch in children:
    if ch.tag == q("sectPr"):
        final = ch

seg = children[break_idx + 1:]
removed = 0
for i, ch in enumerate(seg):
    if a <= i < b:
        continue
    if ch is final:
        continue
    body.remove(ch)
    removed += 1

out = etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
zout = zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED)
for item in zin.infolist():
    data = zin.read(item.filename)
    if item.filename == "word/document.xml":
        data = out
    zout.writestr(item, data)
zout.close()
print(f"break_idx={break_idx} 保留正文 [{a},{b}) 删除 {removed} -> {dst}")

# -*- coding: utf-8 -*-
r"""生成用于二分定位的变体：把分节符之后（第 2 节）的正文全部删掉，
只保留封面/修订记录/目录/简介区（含我填过的前言/范围/背景/缩略语/修订记录）。

用法: python make_variant_v1.py <输入.docx> <输出.docx>
"""
import sys
import zipfile

from lxml import etree

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def q(t):
    return f"{{{W}}}{t}"


src, dst = sys.argv[1], sys.argv[2]
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

removed = 0
for ch in children[break_idx + 1:]:
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
print(f"break_idx={break_idx} removed={removed} -> {dst}")

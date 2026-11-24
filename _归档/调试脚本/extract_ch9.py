# -*- coding: utf-8 -*-
import pymupdf
import sys

SRC = r"E:\xwechat_files\wxid_ifph2dohbkn729_0e86\msg\file\2026-09\chapter9.pdf"
OUT = r"D:\STM32_Project\chapter9.txt"

doc = pymupdf.open(SRC)
lines = []
for i, page in enumerate(doc):
    lines.append("\n========== PAGE %d / %d ==========\n" % (i + 1, len(doc)))
    lines.append(page.get_text())
text = "".join(lines)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(text)

print("pages:", len(doc))
print("chars:", len(text))
print("saved:", OUT)

# -*- coding: utf-8 -*-
"""打印 MCU 页左侧引脚表每个词的确切坐标，精确还原列结构。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
page = doc[2]

for y0, y1, label in ((205, 260, "左侧网标/脚名列"), (200, 260, "右侧 MCU 列")):
    clip = pymupdf.Rect(0, y0, page.rect.width, y1)
    ws = page.get_text("words", clip=clip)
    print("\n===== %s  (y %d~%d) =====" % (label, y0, y1))
    for w in sorted(ws, key=lambda w: (round(w[1], 1), w[0])):
        print("  x=%7.2f y=%6.2f  %-14s" % (w[0], w[1], w[4]))

doc.close()

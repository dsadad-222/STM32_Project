# -*- coding: utf-8 -*-
"""打印右列 KEY1/KEY2/KEY3/LRGB-B/PG 区 每个文字对象的精确 y 与 x，用于逐行对齐。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
page = doc[2]

items = []
for b in page.get_text("dict")["blocks"]:
    if b.get("type") != 0:
        continue
    for l in b["lines"]:
        for s in l["spans"]:
            t = s["text"].strip()
            if not t:
                continue
            x0, y0, x1, y1 = s["bbox"]
            yc = (y0 + y1) / 2.0
            if 185 <= yc <= 235 and 180 <= x0 <= 380:
                items.append((round(yc, 2), round(x0, 1), t))

items.sort()
for yc, x0, t in items:
    print("y=%7.2f  x=%6.1f  %s" % (yc, x0, t))

# 同时输出这一带的所有水平线段
print("\n--- 水平线段(引脚线) ---")
segs = []
for d in page.get_drawings():
    for it in d["items"]:
        if it[0] == "l":
            p1, p2 = it[1], it[2]
            if abs(p1.y - p2.y) < 0.3 and 180 <= p1.y <= 235 and abs(p2.x - p1.x) > 20:
                segs.append((round(p1.y, 2), round(min(p1.x, p2.x), 1), round(max(p1.x, p2.x), 1)))
        elif it[0] == "re":
            r = it[1]
            if r.height < 0.6 and r.width > 20 and 180 <= r.y0 <= 235:
                segs.append((round(r.y0, 2), round(r.x0, 1), round(r.x1, 1)))
for s in sorted(set(segs)):
    print("y=%7.2f  x %.1f .. %.1f" % s)

doc.close()

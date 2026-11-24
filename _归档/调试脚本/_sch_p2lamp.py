# -*- coding: utf-8 -*-
"""提取第2页左上角两个 RGB 灯电路区域的全部文字+线段，判定各自网络。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF); page = doc[1]
items = []
for b in page.get_text("dict")["blocks"]:
    if b.get("type") != 0: continue
    for l in b["lines"]:
        for s in l["spans"]:
            t = s["text"].strip()
            if not t: continue
            x0, y0, x1, y1 = s["bbox"]
            if x0 <= 260 and y0 <= 200:
                items.append((round((y0+y1)/2, 2), round(x0, 1), t))
items.sort()
for yc, x0, t in items:
    print("y=%7.2f x=%6.1f  %s" % (yc, x0, t))
print("\n--- 水平/垂直线段 ---")
segs = set()
for d in page.get_drawings():
    for it in d["items"]:
        if it[0] == "l":
            p1, p2 = it[1], it[2]
            if abs(p1.y-p2.y) < 0.3 and abs(p2.x-p1.x) > 6 and p1.y <= 200 and min(p1.x,p2.x) <= 260:
                segs.add(("H", round(p1.y,2), round(min(p1.x,p2.x),1), round(max(p1.x,p2.x),1)))
            elif abs(p1.x-p2.x) < 0.3 and abs(p2.y-p1.y) > 6 and min(p1.y,p2.y) <= 200 and p1.x <= 260:
                segs.add(("V", round(p1.x,2), round(min(p1.y,p2.y),1), round(max(p1.y,p2.y),1)))
for s in sorted(segs):
    print(s)
doc.close()

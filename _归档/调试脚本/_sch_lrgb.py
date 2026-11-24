# -*- coding: utf-8 -*-
"""在所有页中搜索 LRGB-* / PG0 / PG1 / PE7 / RGB 灯相关网络，输出坐标与附近文字。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
TARGETS = ["LRGB-R", "LRGB-G", "LRGB-B", "LRGB", "RLED", "PG0", "PG1", "PE7", "RGB", "LED1", "LED2"]
for pno in range(doc.page_count):
    page = doc[pno]
    hits = []
    for t in TARGETS:
        for r in page.search_for(t):
            hits.append((round(r.y0, 1), round(r.x0, 1), t))
    if not hits:
        continue
    print("\n========== 第 %d 页 ==========" % (pno + 1))
    for y, x, t in sorted(set(hits)):
        # 找附近文字
        ctx = []
        for b in page.get_text("dict")["blocks"]:
            if b.get("type") != 0: continue
            for l in b["lines"]:
                for s in l["spans"]:
                    st = s["text"].strip()
                    if not st: continue
                    bx0, by0, bx1, by1 = s["bbox"]
                    if abs((by0+by1)/2 - (y+4)) <= 8 and abs(bx0 - x) <= 90 and st != t:
                        ctx.append(st)
        print("  %-8s x=%6.1f y=%6.1f   ctx: %s" % (t, x, y, " ".join(ctx[:8])))
doc.close()

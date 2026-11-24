# -*- coding: utf-8 -*-
"""列出原理图中所有 LRGB / PG0 / PG1 / PG2 / RLED / PE2-PE4 出现的坐标与上下文。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)

TARGETS = ["LRGB-R", "LRGB-G", "LRGB-B", "LRGB", "RLED-R", "RLED-G", "RLED-B", "RLED",
           "PG0", "PG1", "PG2", "PE2", "PE3", "PE4", "LED1", "LED2", "Buzzer", "KEY1", "KEY2", "KEY3",
           "PF11", "PF12", "ECHO"]
for pno in range(doc.page_count):
    page = doc[pno]
    print("\n================ 第 %d 页 ================" % (pno + 1))
    for t in TARGETS:
        rects = page.search_for(t)
        if not rects:
            continue
        coords = ["(%.0f,%.0f)" % (r.x0, r.y0) for r in rects]
        print("  %-8s x%d  %s" % (t, len(rects), " ".join(coords)))

doc.close()

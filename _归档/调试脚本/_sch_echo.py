# -*- coding: utf-8 -*-
"""在 MCU 页(第3页) 定位 ECHO / PF11 / PF12 网标的坐标，并裁切放大。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
doc = pymupdf.open(PDF)
page = doc[2]                      # 第 3 页 = MCU
W, H = page.rect.width, page.rect.height

targets = ["ECHO", "TRIG", "PF11", "PF12", "PF10", "PF13"]
print("--- 第3页 网标坐标 ---")
for t in targets:
    rects = page.search_for(t)
    print("%-6s 命中 %d 处: %s" % (t, len(rects),
          [(round(r.x0), round(r.y0), round(r.x1), round(r.y1)) for r in rects]))

# 裁 ECHO 出现的位置周围
for t in ["ECHO", "PF12"]:
    for i, r in enumerate(page.search_for(t)):
        clip = pymupdf.Rect(max(0, r.x0 - 150), max(0, r.y0 - 90),
                            min(W, r.x1 + 260), min(H, r.y1 + 90))
        pix = page.get_pixmap(dpi=600, clip=clip)
        p = os.path.join(OUT, "p3_%s_%d.png" % (t, i))
        pix.save(p)
        print("->", p, pix.width, "x", pix.height)

doc.close()

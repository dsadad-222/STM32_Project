# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
doc = pymupdf.open(PDF); page = doc[0]
for k in ["灯条", "灯", "RGB", "LRGB"]:
    for r in page.search_for(k):
        print("%-6s x=%6.1f y=%6.1f" % (k, r.x0, r.y0))
pix = page.get_pixmap(matrix=pymupdf.Matrix(6, 6), clip=pymupdf.Rect(370, 40, 480, 105))
p = os.path.join(OUT, "p1_lampblock.png"); pix.save(p); print(p, pix.width, pix.height)
doc.close()

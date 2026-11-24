# -*- coding: utf-8 -*-
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
doc = pymupdf.open(PDF); page = doc[1]
pix = page.get_pixmap(matrix=pymupdf.Matrix(11, 11), clip=pymupdf.Rect(25, 128, 145, 172))
p = os.path.join(OUT, "p2_lamp2.png"); pix.save(p)
print(p, pix.width, pix.height)
# 同时把所有含 LED / RGB 的文本列出
print("\n--- 第2页 含 LED/RGB 的文字 ---")
for b in page.get_text("dict")["blocks"]:
    if b.get("type") != 0: continue
    for l in b["lines"]:
        for s in l["spans"]:
            t = s["text"].strip()
            if any(k in t.upper() for k in ("LED", "RGB")):
                print("  y=%6.1f x=%6.1f  %s" % ((s["bbox"][1]+s["bbox"][3])/2, s["bbox"][0], t))
doc.close()

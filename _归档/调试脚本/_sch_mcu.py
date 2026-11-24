# -*- coding: utf-8 -*-
"""裁切 MCU 页左右两半的引脚表，逐列核对。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
doc = pymupdf.open(PDF)
page = doc[2]
W, H = page.rect.width, page.rect.height

# 左半（外部网标 + MCU脚名/脚号）与右半（MCU脚名/脚号 + 内部网标）
left  = pymupdf.Rect(0.20 * W, 0.30 * H, 0.34 * W, 0.72 * H)
right = pymupdf.Rect(0.28 * W, 0.30 * H, 0.46 * W, 0.72 * H)
for name, r in (("p3_left", left), ("p3_right", right)):
    pix = page.get_pixmap(dpi=700, clip=r)
    p = os.path.join(OUT, name + ".png")
    pix.save(p)
    print("->", p, pix.width, "x", pix.height)

doc.close()

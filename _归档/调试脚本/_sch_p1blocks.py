# -*- coding: utf-8 -*-
"""渲染第1页各功能块，人工读取引脚分配。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
doc = pymupdf.open(PDF)
page = doc[0]
CROPS = {
    "p1_oled_usart.png": (95, 120, 340, 235),
    "p1_flash.png":      (300, 180, 440, 230),
    "p1_lamp.png":       (380, 55, 470, 100),
}
for name, (x0, y0, x1, y1) in CROPS.items():
    pix = page.get_pixmap(matrix=pymupdf.Matrix(8, 8), clip=pymupdf.Rect(x0, y0, x1, y1))
    p = os.path.join(OUT, name); pix.save(p)
    print("%-22s %dx%d -> %s" % (name, pix.width, pix.height, p))
doc.close()

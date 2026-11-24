# -*- coding: utf-8 -*-
"""高倍渲染 MCU 符号右列(PE/PG 区)与左列(PF 区)，人工核对引脚号。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
os.makedirs(OUT, exist_ok=True)
doc = pymupdf.open(PDF)
page = doc[2]

CROPS = {
    "v_right_top.png":  (275, 105, 400, 190),   # PG15..PG10 区
    "v_right_mid.png":  (275, 185, 400, 265),   # PG9..PE8 区
    "v_left_pf.png":    (180, 210, 280, 265),   # PF11..PE7 区
    "v_left_full.png":  (180, 105, 280, 270),   # 左列全
}
ZOOM = 9.0
for name, (x0, y0, x1, y1) in CROPS.items():
    clip = pymupdf.Rect(x0, y0, x1, y1)
    pix = page.get_pixmap(matrix=pymupdf.Matrix(ZOOM, ZOOM), clip=clip)
    p = os.path.join(OUT, name)
    pix.save(p)
    print("%-20s %dx%d -> %s" % (name, pix.width, pix.height, p))

doc.close()

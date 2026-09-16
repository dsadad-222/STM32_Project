# -*- coding: utf-8 -*-
import pymupdf, os
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\sch_crop"
os.makedirs(OUT, exist_ok=True)
doc = pymupdf.open(PDF)
jobs = [
    (1, (130, 100, 250, 165), "J1_ultrasonic", 8),
    (2, (150, 190, 290, 260), "MCU_ECHO_area", 8),
    (2, (280, 125, 380, 175), "MCU_HS0038B_area", 8),
]
for pi, box, name, zoom in jobs:
    pg = doc[pi]
    clip = pymupdf.Rect(*box)
    pix = pg.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom), clip=clip)
    p = os.path.join(OUT, f"{name}.png")
    pix.save(p)
    print(f"{p}  {pix.width}x{pix.height}")

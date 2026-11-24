# -*- coding: utf-8 -*-
"""裁切放大原理图关键区域：超声波 J1 / MCU 页 PF11-PF12 / W25Q64 / LED / 按键。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
os.makedirs(OUT, exist_ok=True)
doc = pymupdf.open(PDF)

W, H = doc[1].rect.width, doc[1].rect.height
print("页面尺寸:", W, "x", H)

# 超声波区（页2 左上第2栏）：按比例估算
clips = [
    ("p2_ultrasonic", 1, (0.145, 0.13, 0.28, 0.32)),
    ("p2_rgb",        1, (0.02,  0.10, 0.15, 0.28)),
    ("p2_led",        1, (0.86,  0.42, 1.00, 0.60)),
    ("p2_buzzer",     1, (0.86,  0.86, 1.00, 1.00)),
]
for name, pno, (x0, y0, x1, y1) in clips:
    r = pymupdf.Rect(x0 * W, y0 * H, x1 * W, y1 * H)
    pix = doc[pno].get_pixmap(dpi=600, clip=r)
    path = os.path.join(OUT, name + ".png")
    pix.save(path)
    print("->", path, pix.width, "x", pix.height)

doc.close()

# -*- coding: utf-8 -*-
"""裁切页2 的 RGB灯 / LED灯 区域，读 LRGB-R/G/B 与 RLED-R/G/B 的网标。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
doc = pymupdf.open(PDF)
p2 = doc[1]
W, H = p2.rect.width, p2.rect.height

clips = [
    ("p2_rgb_lamp", (0.02, 0.09, 0.16, 0.24)),   # 左上 RGB灯
    ("p2_led_lamp", (0.86, 0.40, 1.00, 0.58)),   # 右下 LED灯
]
for name, (x0, y0, x1, y1) in clips:
    r = pymupdf.Rect(x0 * W, y0 * H, x1 * W, y1 * H)
    pix = p2.get_pixmap(dpi=700, clip=r)
    p = os.path.join(OUT, name + ".png")
    pix.save(p)
    print("->", p, pix.width, "x", pix.height)

# 页3 右侧半（MCU 内部网标列）单独再裁一次，窄一点
p3 = doc[2]
r = pymupdf.Rect(0.36 * W, 0.30 * H, 0.46 * W, 0.72 * H)
pix = p3.get_pixmap(dpi=700, clip=r)
p = os.path.join(OUT, "p3_right2.png")
pix.save(p)
print("->", p, pix.width, "x", pix.height)

doc.close()

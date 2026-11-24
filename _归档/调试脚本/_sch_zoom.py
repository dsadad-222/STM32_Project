# -*- coding: utf-8 -*-
"""极限放大 MCU 符号左下角（PG0/PG1/PG2 那几行），肉眼确认列对齐。"""
import sys, io, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
doc = pymupdf.open(PDF)
p = doc[2]

# 左下角：脚号 55~58 + 网标 LRGB-R/G
r1 = pymupdf.Rect(180, 236, 320, 264)
pix = p.get_pixmap(dpi=1200, clip=r1); pix.save(os.path.join(OUT, "zoom_left_bottom.png"))
print("-> zoom_left_bottom.png", pix.width, pix.height)

# 右上：LRGB-B / pin 87 / PG2
r2 = pymupdf.Rect(285, 202, 380, 216)
pix = p.get_pixmap(dpi=1200, clip=r2); pix.save(os.path.join(OUT, "zoom_right_rgbb.png"))
print("-> zoom_right_rgbb.png", pix.width, pix.height)

# 左上：PF11/ECHO 那几行（复核超声波）
r3 = pymupdf.Rect(180, 212, 320, 230)
pix = p.get_pixmap(dpi=1200, clip=r3); pix.save(os.path.join(OUT, "zoom_left_ultrasonic.png"))
print("-> zoom_left_ultrasonic.png", pix.width, pix.height)

doc.close()

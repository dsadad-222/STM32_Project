# -*- coding: utf-8 -*-
"""看 PB12-15 右侧的网络名 + W25Q64 周边网络。"""
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)

print("########## page3 : PB12-PB15 右侧网络 (x 470~700, y 218~252) ##########")
for w in doc[2].get_text("words"):
    x0, y0, txt = w[0], w[1], w[4]
    if 470 <= x0 <= 700 and 218 <= y0 <= 252:
        print(f"  ({x0:7.1f},{y0:7.1f})  {txt}")

print("\n########## page1 : W25Q64 周边 (x 300~460, y 175~230) ##########")
for w in doc[0].get_text("words"):
    x0, y0, txt = w[0], w[1], w[4]
    if 300 <= x0 <= 460 and 175 <= y0 <= 232:
        print(f"  ({x0:7.1f},{y0:7.1f})  {txt}")

print("\n########## page1 : OLED 周边 (x 230~320, y 210~260) ##########")
for w in doc[0].get_text("words"):
    x0, y0, txt = w[0], w[1], w[4]
    if 230 <= x0 <= 330 and 205 <= y0 <= 265:
        print(f"  ({x0:7.1f},{y0:7.1f})  {txt}")

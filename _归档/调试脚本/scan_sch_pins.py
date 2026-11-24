# -*- coding: utf-8 -*-
"""精确提取 OLED / W25Q64 / I2C1 / SPI2 的引脚归属。"""
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)

def dump(pno, keys, title):
    print(f"\n########## {title} (page {pno+1}) ##########")
    page = doc[pno]
    for w in page.get_text("words"):
        x0, y0, x1, y1, txt = w[0], w[1], w[2], w[3], w[4]
        if any(k.lower() in txt.lower() for k in keys):
            print(f"  ({x0:7.1f},{y0:7.1f})  {txt}")

# page1: OLED 与 W25Q64 所在分区图
dump(0, ["OLED", "W25Q64", "0.86"], "page1 OLED/Flash")
# page3: MCU sheet 的 I2C1 / SPI2 引脚
dump(2, ["I2C1", "SPI2", "PB6", "PB7", "PB13", "PB14", "PB15", "PB12"], "page3 MCU 引脚")

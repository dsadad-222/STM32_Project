# -*- coding: utf-8 -*-
"""在原理图里找"屏幕/显示"相关的网络与器件。"""
import pymupdf, re

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
print("pages =", doc.page_count)

KEY = ["OLED", "LCD", "TFT", "屏幕", "SPI", "FLASH", "W25", "I2C", "IIC",
       "SCL", "SDA", "CS", "MOSI", "MISO", "SCK", "DC", "RES", "BLK", "BL"]

for pno in range(doc.page_count):
    page = doc[pno]
    txt = page.get_text()
    lines = [l.strip() for l in txt.splitlines() if l.strip()]
    hits = [l for l in lines if any(k.lower() in l.lower() for k in KEY)]
    print(f"\n===== page {pno+1}  (总 {len(lines)} 行, 命中 {len(hits)}) =====")
    for h in hits[:120]:
        print("  ", h)

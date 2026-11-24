# -*- coding: utf-8 -*-
"""第2页：搜索 FLASH/OLED/USART/超声波 等外围电路的网络名与标注。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
KEY = ["W25Q64", "W25Q", "FLASH", "Flash", "SPI", "OLED", "I2C", "USART", "UART", "TXD", "RXD",
       "PB12", "PB13", "PB14", "PB15", "PB6", "PB7", "PA9", "PA10", "CS", "SCK", "MISO", "MOSI",
       "SCL", "SDA", "PF11", "PF12", "ECHO", "TRIG", "J1", "J2", "J3"]
for pno in range(doc.page_count):
    page = doc[pno]
    found = {}
    for k in KEY:
        rs = page.search_for(k)
        if rs:
            found[k] = sorted(set((round(r.y0, 1), round(r.x0, 1)) for r in rs))
    if not found:
        continue
    print("\n########## 第 %d 页 ##########" % (pno + 1))
    for k, v in found.items():
        print("  %-8s x%d  %s" % (k, len(v), " ".join("(%g,%g)" % (x, y) for y, x in v[:12])))
doc.close()

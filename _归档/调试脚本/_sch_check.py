# -*- coding: utf-8 -*-
"""从 YB-DSF01-V1.0.pdf 提取网标，核对需求4 涉及的全部引脚。"""
import sys, io, re, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
OUT = r"D:\STM32_Project\_sch_render"
os.makedirs(OUT, exist_ok=True)

doc = pymupdf.open(PDF)
print("页数:", doc.page_count)

# 1) 每页文本，找关键词
KEYWORDS = ["PF11", "PF12", "TRIG", "ECHO", "Ultrasonic", "ULTRASONIC", "超声波",
            "PG12", "PG14", "PG15", "PG3", "PG4", "PG5", "PB12", "PB13", "PB14", "PB15",
            "PB6", "PB7", "PA9", "PA10", "PE2", "PE3", "PE4", "PG0", "PG1", "PG2",
            "W25Q64", "SSD1306", "OLED", "Buzzer", "BUZZER", "KEY1", "KEY2", "KEY3",
            "LED1", "LED2", "LRGB", "RLED"]

pages_text = []
for i, page in enumerate(doc):
    t = page.get_text()
    pages_text.append(t)

for kw in KEYWORDS:
    hits = [i + 1 for i, t in enumerate(pages_text) if kw.lower() in t.lower()]
    print("%-12s -> 页 %s" % (kw, hits if hits else "未命中"))

# 2) 把含 PF11/PF12 的页面渲染出来
target_pages = set()
for i, t in enumerate(pages_text):
    if ("PF11" in t) or ("PF12" in t) or ("Ultrasonic" in t) or ("W25Q64" in t):
        target_pages.add(i)
print("\n渲染页:", sorted(p + 1 for p in target_pages))

for p in sorted(target_pages):
    pix = doc[p].get_pixmap(dpi=220)
    path = os.path.join(OUT, "page%02d.png" % (p + 1))
    pix.save(path)
    print("  ->", path, pix.width, "x", pix.height)

doc.close()

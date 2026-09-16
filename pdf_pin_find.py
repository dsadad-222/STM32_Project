# -*- coding: utf-8 -*-
"""坐标级提取原理图：找 J1(超声波) 的 TRIG 走线、HS0038B 的红外输出脚"""
import pymupdf, re, sys
PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
print("页数:", doc.page_count)
for i, pg in enumerate(doc):
    r = pg.rect
    print(f"  页{i}: {r.width:.0f} x {r.height:.0f}  旋转{pg.rotation}")

def words(page):
    return page.get_text("words")   # x0,y0,x1,y1,word,block,line,word_no

KEYS = ["TRIG", "ECHO", "Ultrasonic", "HS0038", "RIG"]
for i, pg in enumerate(doc):
    ws = words(pg)
    hit = [(w) for w in ws if any(k in w[4] for k in KEYS)]
    if hit:
        print(f"\n===== 页{i} 命中 {len(hit)} =====")
        for w in hit:
            print(f"   ({w[0]:7.1f},{w[1]:7.1f}) {w[4]}")

# -*- coding: utf-8 -*-
"""按坐标重建 MCU 页的引脚表，逐行对齐 [外部网标][脚名 脚号][MCU GPIO]。"""
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)
page = doc[2]

# 取 MCU 符号区域的词
CLIP = pymupdf.Rect(0.20 * page.rect.width, 0.30 * page.rect.height,
                    0.46 * page.rect.width, 0.75 * page.rect.height)
words = page.get_text("words", clip=CLIP)
print("词数:", len(words))

# 按 y 分行（容差 3pt）
words.sort(key=lambda w: (round(w[1] / 3.0), w[0]))
rows = []
cur_y = None
cur = []
for w in words:
    y = w[1]
    if cur_y is None or abs(y - cur_y) <= 3.0:
        cur.append(w)
        cur_y = y if cur_y is None else cur_y
    else:
        rows.append((cur_y, sorted(cur, key=lambda x: x[0])))
        cur = [w]
        cur_y = y
if cur:
    rows.append((cur_y, sorted(cur, key=lambda x: x[0])))

print("\n%-6s %-42s %-34s %s" % ("y", "左半(网标 | 脚名 脚号)", "MCU GPIO", "右半"))
print("-" * 130)
for y, ws in rows:
    # 按 x 分三带：左(网标) / 中(脚名+脚号) / 右(MCU GPIO)
    left, mid, right = [], [], []
    for w in ws:
        x0 = w[0]
        if x0 < 0.262 * page.rect.width:
            left.append(w[4])
        elif x0 < 0.315 * page.rect.width:
            mid.append(w[4])
        else:
            right.append(w[4])
    if not (left or mid or right):
        continue
    print("%-6.1f %-42s %-34s %s" % (y, " ".join(left), " ".join(mid), " ".join(right)))

doc.close()

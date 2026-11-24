# -*- coding: utf-8 -*-
"""定位 I2C1 网络在原理图上的位置并渲染局部图，确认上拉电阻。"""
import pymupdf

PDF = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\file\2026-09\幼专培训(1)\幼专培训\第1阶段\3-电路原理图\YB-DSF01-V1.0.pdf"
doc = pymupdf.open(PDF)

hits = {}
for pno in range(doc.page_count):
    for w in doc[pno].get_text("words"):
        if "I2C1" in w[4]:
            hits.setdefault(pno, []).append((round(w[0], 1), round(w[1], 1), w[4]))

for pno, lst in sorted(hits.items()):
    print(f"page {pno+1}: {len(lst)} 处")
    for x, y, t in sorted(set(lst)):
        print(f"    ({x:7.1f},{y:7.1f})  {t}")

# 渲染每页 I2C1 出现的局部区域，找上拉电阻
import os
os.makedirs(r"D:\Temp\sch", exist_ok=True)
for pno, lst in sorted(hits.items()):
    xs = [x for x, y, t in lst]; ys = [y for x, y, t in lst]
    # 取最上面一组做局部放大
    y0 = min(ys)
    sel = [(x, y) for x, y in zip(xs, ys) if abs(y - y0) < 40]
    if not sel:
        continue
    x0 = min(x for x, y in sel); x1 = max(x for x, y in sel)
    rect = pymupdf.Rect(max(0, x0 - 60), max(0, y0 - 45), x1 + 60, y0 + 45)
    pix = doc[pno].get_pixmap(matrix=pymupdf.Matrix(5, 5), clip=rect)
    out = rf"D:\Temp\sch\i2c1_p{pno+1}.png"
    pix.save(out)
    print("saved ->", out, pix.width, "x", pix.height, " rect =", rect)

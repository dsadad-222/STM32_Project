# -*- coding: utf-8 -*-
"""细看左右两颗灯珠的丝印"""
from PIL import Image
import os

SRC = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\temp\RWTemp\2026-09\9e20f478899dc29eb19741386f9343c8\b91afe0b9d913e1315ac440dc2643b6c.jpg"
OUT = r"C:\Users\y7000\Desktop\嵌入式"

img = Image.open(SRC)

crops = [
    ("右上灯丝印", (740, 280, 1080, 500), 7),
    ("左上灯丝印", (240, 280, 580, 500), 7),
]

for name, box, scale in crops:
    c = img.crop(box)
    c = c.resize((c.width * scale, c.height * scale), Image.LANCZOS)
    # 提亮 + 锐化，丝印更好认
    from PIL import ImageEnhance
    c = ImageEnhance.Brightness(c).enhance(1.4)
    c = ImageEnhance.Contrast(c).enhance(1.5)
    p = os.path.join(OUT, "板子特写_%s.png" % name)
    c.save(p)
    print(name, box, "->", c.size)

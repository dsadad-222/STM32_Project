# -*- coding: utf-8 -*-
"""
make_keyoled_report.py —— 把两次读回的显存拼成一张「上板验证报告图」

左：上电第一屏    右：按一次 KEY1 之后
图上的像素全部来自板上真实 RAM（s_gram @0x2000008C）读回的数据，
不是按字库重画的示意图。
"""

import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))

OLED_W, OLED_H, PAGE_N = 128, 32, 4
SCALE = 8
PAD, BAND = 24, 64

# 中文字体（PIL 默认字体不支持中文）
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
    r"C:\Windows\Fonts\simsun.ttc",
]


def load_font(size):
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:                                     # noqa: BLE001
                continue
    return ImageFont.load_default()


def panel(draw, raw, ox, oy, title, sub):
    f_title = load_font(22)
    f_sub = load_font(16)

    draw.text((ox, oy - 58), title, fill=(235, 240, 250), font=f_title)
    draw.text((ox, oy - 32), sub, fill=(140, 152, 175), font=f_sub)

    draw.rectangle([ox - 2, oy - 2, ox + OLED_W * SCALE + 1, oy + OLED_H * SCALE + 1],
                   outline=(90, 100, 125), fill=(0, 0, 0))
    for page in range(PAGE_N):
        for x in range(OLED_W):
            b = raw[page * OLED_W + x]
            for y in range(8):
                if (b >> y) & 1:
                    px, py = ox + x * SCALE, oy + (page * 8 + y) * SCALE
                    draw.rectangle([px, py, px + SCALE - 1, py + SCALE - 1],
                                   fill=(150, 210, 255))


def main():
    name = open(os.path.join(HERE, "_gram_poweron.bin"), "rb").read()
    call = open(os.path.join(HERE, "_gram_after_key1.bin"), "rb").read()

    W = PAD * 3 + OLED_W * SCALE * 2
    H = 150 + OLED_H * SCALE + PAD
    img = Image.new("RGB", (W, H), (22, 24, 30))
    d = ImageDraw.Draw(img)

    f_h = load_font(26)
    f_n = load_font(15)
    d.text((PAD, 28), "KeyOled_Full  上板验证", fill=(240, 244, 252), font=f_h)
    d.text((PAD, 66), "两块屏的像素均来自板上真实 RAM（s_gram @0x2000008C）读回，非示意图",
           fill=(130, 142, 165), font=f_n)

    y = 150
    panel(d, name, PAD, y, "上电第一屏", "md5 f57cdb58…")
    panel(d, call, PAD * 2 + OLED_W * SCALE, y, "按一次 KEY1 后", "md5 0d876367…")

    out = os.path.join(HERE, "KeyOled_Full", "Doc", "上板验证_李登辉与叫爸爸.png")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    img.save(out)
    print("已生成: %s  (%dx%d)" % (out, W, H))


if __name__ == "__main__":
    main()

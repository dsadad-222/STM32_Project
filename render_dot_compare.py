# -*- coding: utf-8 -*-
"""对比放大字里小数点的三种画法（4x4 原字模 / 6x6 / 8x8 加粗），
其余部分（"温度" 汉字 + 数字）与固件完全一致，输出一张对比 PNG。"""

import sys

sys.path.insert(0, r"D:\STM32_Project")

from render_oled_cn import FONT, W, H, draw_cn, write_png   # noqa: E402

OUT = r"C:\Users\y7000\Desktop\嵌入式\OLED小数点对比_4x4_6x6_8x8.png"


def dot_mask(h):
    """高 h 像素、贴着下限画在 page+1（第 8~15 行）里的位掩码"""
    return ((1 << h) - 1) << (8 - h)


def draw_big(canvas, col, page, ch, dot=0):
    """dot = 0 表示用字模原样；否则用 dot x dot 的实心方块画小数点"""
    if ch == "." and dot:
        x0 = col * 16 + (16 - dot) // 2
        mask = dot_mask(dot)
        for i in range(dot):
            byte = mask
            for k in range(8):
                if byte & (1 << k):
                    canvas[(page * 8 + 8 + k) * W + x0 + i] = 1
        return

    code = ord(ch)
    glyph = FONT[code - 0x20]
    for cx in range(8):
        lo = hi = 0
        for cy in range(8):
            if glyph[cy] & (0x80 >> cx):
                if cy < 4:
                    lo |= 0x03 << (cy * 2)
                else:
                    hi |= 0x03 << ((cy - 4) * 2)
        for dx in (0, 1):
            x = col * 16 + cx * 2 + dx
            y0 = page * 8
            for k in range(8):
                if lo & (1 << k):
                    canvas[(y0 + k) * W + x] = 1
                if hi & (1 << k):
                    canvas[(y0 + 8 + k) * W + x] = 1


def build(dot):
    c = [0] * (W * H)
    draw_cn(c, 0, 0, "温")
    draw_cn(c, 1, 0, "度")
    for i, ch in enumerate("33.6C"):
        draw_big(c, 3 + i, 0, ch, dot)
    # 状态行：8x8 小字，两种方案一样，仅作对照
    from render_oled_cn import draw_char8
    for i, ch in enumerate("L0 R0 B0 D1   RST"[:16]):
        draw_char8(c, i, 3, ch)
    return c


if __name__ == "__main__":
    write_png(OUT, [build(0), build(6), build(8)], scale=6, gap=20)
    print("左=字模原样(4x4)  中=6x6  右=8x8")

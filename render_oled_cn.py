# -*- coding: utf-8 -*-
"""
按固件同样的写入算法，渲染中文版 OLED 两个页面的真机效果预览：
  温度页：大字“温度 35.9C” + ADC 原始值/电压行 + 状态行
  文本页：32 字符文本 + 中文提示大字（标定完成）居中
输出 PNG 到桌面（纯 Python 编码，无第三方依赖）。
"""

import io
import re
import struct
import zlib

from gen_cn_font import render as render_cn   # 复用 GDI 取模

FONT8X8_C = r"D:\STM32_Project\AdcTemp_Full\Drv_Common\font8x8.c"
OUT_PNG = r"C:\Users\y7000\Desktop\嵌入式\OLED中文版_真机效果预览.png"

W, H = 128, 32


def load_font8x8():
    with io.open(FONT8X8_C, "r", encoding="utf-8") as f:
        src = f.read()
    rows = re.findall(r"\{((?:0x[0-9A-Fa-f]{2}\s*,\s*){7}0x[0-9A-Fa-f]{2})\}", src)
    table = []
    for r in rows:
        table.append([int(x, 16) for x in r.split(",")])
    assert len(table) == 95, len(table)
    return table            # index 0 = 0x20


FONT = load_font8x8()


def draw_char8(canvas, col, row, ch):
    """8x8 字符，与 OLED_ShowChar 相同的转置写入"""
    code = ord(ch)
    if code < 0x20 or code > 0x7E:
        ch = "?"
        code = 0x3F
    glyph = FONT[code - 0x20]
    for cx in range(8):
        byte = 0
        for cy in range(8):
            if glyph[cy] & (0x80 >> cx):
                byte |= (1 << cy)
        x = col * 8 + cx
        y0 = row * 8
        for k in range(8):
            if byte & (1 << k):
                canvas[(y0 + k) * W + x] = 1


def draw_char_big(canvas, col, page, ch):
    """16x16 放大字（8x8 字模行列各 2 倍），与 OLED_ShowCharBig 相同"""
    code = ord(ch)
    if code < 0x20 or code > 0x7E:
        code = 0x3F
    glyph = FONT[code - 0x20]
    for cx in range(8):
        lo = hi = 0
        for cy in range(8):
            if glyph[cy] & (0x80 >> cx):
                if cy < 4:
                    lo |= (0x03 << (cy * 2))
                else:
                    hi |= (0x03 << ((cy - 4) * 2))
        for dx in range(2):
            x = col * 16 + cx * 2 + dx
            for k in range(8):
                y = page * 8 + k
                if lo & (1 << k):
                    canvas[y * W + x] = 1
                y2 = (page + 1) * 8 + k
                if hi & (1 << k):
                    canvas[y2 * W + x] = 1


def draw_cn(canvas, col, page, ch):
    """16x16 汉字，与 OLED_ShowCNChar 相同的转置写入"""
    data = render_cn(ch)
    for x in range(16):
        lo = hi = 0
        for y in range(8):
            if data[y * 2 + (x >> 3)] >> (7 - (x & 7)) & 1:
                lo |= (1 << y)
        for y in range(8):
            if data[(y + 8) * 2 + (x >> 3)] >> (7 - (x & 7)) & 1:
                hi |= (1 << y)
        for k in range(8):
            if lo & (1 << k):
                canvas[(page * 8 + k) * W + col * 16 + x] = 1
            if hi & (1 << k):
                canvas[((page + 1) * 8 + k) * W + col * 16 + x] = 1


def pad16(s):
    return (s + " " * 16)[:16]


def build_temp_page():
    c = [0] * (W * H)
    # 上半屏：温度（汉字 col0-1）+ 空格 + 数值（col3-7）
    draw_cn(c, 0, 0, "温")
    draw_cn(c, 1, 0, "度")
    num = "35.9C"
    for i, ch in enumerate(num):
        draw_char_big(c, 3 + i, 0, ch)
    # 第 3 行：ADC 值 + 电压
    line2 = pad16("ADC 1743  1.390 V")
    for i, ch in enumerate(line2):
        draw_char8(c, i, 2, ch)
    # 第 4 行：状态行
    line3 = pad16("L0 R0 B0 D1  RST ")
    for i, ch in enumerate(line3):
        draw_char8(c, i, 3, ch)
    return c


def build_text_page():
    c = [0] * (W * H)
    text = "HELLO CHAPTER8!    "
    for i, ch in enumerate(text[:16]):
        draw_char8(c, i, 0, ch)
    for i, ch in enumerate(text[16:32]):
        draw_char8(c, i, 1, ch)
    # 中文提示 4 个字，居中 (8-4)/2 = col2
    for i, ch in enumerate("标定完成"):
        draw_cn(c, 2 + i, 2, ch)
    return c


def write_png(path, imgs, scale=5, gap=18, label_h=0):
    n = len(imgs)
    w = W * scale
    h = (H * scale + gap) * n
    pixels = bytearray([255] * (w * h))

    for idx, canvas in enumerate(imgs):
        oy = idx * (H * scale + gap)
        for y in range(H):
            for x in range(W):
                if canvas[y * W + x]:
                    for dy in range(scale):
                        for dx in range(scale):
                            pixels[(oy + y * scale + dy) * w + x * scale + dx] = 0
        # 屏幕边框
        for x in range(w):
            if oy > 0:
                pixels[(oy - gap // 2) * w + x] = 210

    raw = b""
    for y in range(h):
        raw += b"\x00" + bytes(pixels[y * w:(y + 1) * w])

    def chunk(tag, data):
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)
    print("写出：", path, "(%dx%d)" % (w, h))


if __name__ == "__main__":
    write_png(OUT_PNG, [build_temp_page(), build_text_page()])

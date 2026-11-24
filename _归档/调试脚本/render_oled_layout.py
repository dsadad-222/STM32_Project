# -*- coding: utf-8 -*-
"""
渲染 OLED（128x32）显示布局：改前 vs 改后，输出 PNG 对比图。
用工程里真实的 font8x8.c 字模，按 oled_drv.c 的同样算法写入 128x32 位图，
保证预览和真机显示完全一致。纯 Python 写 PNG（不依赖 Pillow）。
"""

import re
import zlib
import struct

FONT_SRC = r"D:/STM32_Project/AdcTemp_Full/Drv_Common/font8x8.c"
OUT_PNG  = r"C:/Users/y7000/Desktop/嵌入式/OLED显示布局_改前改后.png"

W, H = 128, 32

# ---------------- 解析字模 ----------------
font = {}
src = open(FONT_SRC, encoding="utf-8", errors="ignore").read()
pat = re.compile(r"\{([^}]*)\},\s*/\*\s*(0x[0-9A-Fa-f]{2})")
for m in pat.finditer(src):
    vals = [int(v, 16) for v in re.findall(r"0x([0-9A-Fa-f]{2})", m.group(1))]
    if len(vals) == 8:
        font[int(m.group(2), 16)] = vals
print("字库字符数:", len(font))

# ---------------- 128x32 像素缓冲 ----------------
px = [[0] * W for _ in range(H)]


def set_px(x, y):
    if 0 <= x < W and 0 <= y < H:
        px[y][x] = 1


def show_char(col, row, ch):
    """对应 oled_drv.c 的 OLED_ShowChar：8x8 小字，col/row 是字符格坐标"""
    g = font.get(ord(ch)) or font.get(ord("?"))
    x0, y0 = col * 8, row * 8
    for cx in range(8):
        for by in range(8):
            if g[by] & (0x80 >> cx):
                set_px(x0 + cx, y0 + by)


def show_string(col, row, s):
    for i, ch in enumerate(s):
        show_char(col + i, row, ch)


def show_char_big(col, page, ch):
    """对应新增的 OLED_ShowCharBig：行列各放大 2 倍，一个字符占 16x16 像素"""
    g = font.get(ord(ch)) or font.get(ord("?"))
    x0, y0 = col * 16, page * 8
    for cx in range(8):
        for by in range(8):
            if g[by] & (0x80 >> cx):
                for dx in (0, 1):
                    for dy in (0, 1):
                        set_px(x0 + cx * 2 + dx, y0 + by * 2 + dy)


def show_string_big(col, page, s):
    for i, ch in enumerate(s):
        if col + i < 8:
            show_char_big(col + i, page, ch)


def render(layout_fn):
    global px
    px = [[0] * W for _ in range(H)]
    layout_fn()
    return px


# ---------------- 两套布局 ----------------
def layout_before():
    """改之前：4 行 8x8 小字，把 32 像素顶满，行间零空隙"""
    show_string(0, 0, "ADCvalue: 1738")
    show_string(0, 1, "Voltage :1.390")
    show_string(0, 2, "Temp    :29.06")
    show_string(0, 3, "L0 R0 B0 D0 CAL")


def layout_after():
    """改之后：第 1 行 16 像素大字温度，下面两行小字左右分栏"""
    show_string_big(0, 0, "29.06 C")
    show_string(0, 2, "ADC  1738 1.390 V")
    show_string(0, 3, "L0 R0 B0 D0 CAL")


before = render(layout_before)
after = render(layout_after)


# ---------------- 画布 ----------------
SCALE  = 5
BG     = (22, 24, 28)
BEZEL  = (78, 84, 96)
LIT    = (236, 246, 255)
LABEL  = (150, 162, 178)

SW = W * SCALE          # 640
SH = H * SCALE          # 160
CX = 12                 # 左边距

lab1_y = 10
scr1_y = lab1_y + 28
lab2_y = scr1_y + SH + 30
scr2_y = lab2_y + 28
CW = SW + CX * 2
CH = scr2_y + SH + 14

canvas = [[BG] * CW for _ in range(CH)]


def put(x, y, c):
    if 0 <= x < CW and 0 <= y < CH:
        canvas[y][x] = c


def draw_screen(bitmap, y0):
    """画一块屏：外框 + 黑底 + 点亮像素"""
    for x in range(CX - 2, CX + SW + 2):
        for y in (y0 - 2, y0 - 1, y0 + SH, y0 + SH + 1):
            put(x, y, BEZEL)
    for y in range(y0 - 2, y0 + SH + 2):
        for x in (CX - 2, CX - 1, CX + SW, CX + SW + 1):
            put(x, y, BEZEL)
    for y in range(H):
        for x in range(W):
            if bitmap[y][x]:
                for dy in range(SCALE):
                    for dx in range(SCALE):
                        put(CX + x * SCALE + dx, y0 + y * SCALE + dy, LIT)


def draw_text(x, y, s, scale, color):
    for i, ch in enumerate(s):
        g = font.get(ord(ch))
        if not g:
            continue
        for by in range(8):
            for cx in range(8):
                if g[by] & (0x80 >> cx):
                    for dy in range(scale):
                        for dx in range(scale):
                            put(x + (i * 8 + cx) * scale + dx,
                                y + by * scale + dy, color)


draw_text(CX, lab1_y, "BEFORE  (4 rows x 8px, no gap)", 3, LABEL)
draw_screen(before, scr1_y)

draw_text(CX, lab2_y, "AFTER  (16px big temp + 2 rows)", 3, LABEL)
draw_screen(after, scr2_y)


# ---------------- 输出 PNG ----------------
def write_png(path, w, h, rows):
    raw = bytearray()
    for row in rows:
        raw.append(0)
        for c in row:
            raw += bytes(c)

    def chunk(tag, data):
        return (struct.pack(">I", len(data)) + tag + data +
                struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

    png = b"\x89PNG\r\n\x1a\n"
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    png += chunk(b"IEND", b"")
    open(path, "wb").write(png)


write_png(OUT_PNG, CW, CH, canvas)
print("已输出:", OUT_PNG, f"({CW}x{CH})")

# ---------------- 附带做一次文字校验 ----------------
lit_old = sum(sum(r) for r in before)
lit_new = sum(sum(r) for r in after)
print(f"点亮像素：改前 {lit_old} / 改后 {lit_new}")
print("改后前两页(大字区)点亮像素:", sum(sum(r) for r in after[0:16]),
      " 后两页(小字区):", sum(sum(r) for r in after[16:32]))

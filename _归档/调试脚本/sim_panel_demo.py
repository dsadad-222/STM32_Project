# -*- coding: utf-8 -*-
"""按匿名版 panel.c 的逻辑渲染屏显，确认排版与含信息版一样可用但不是照搬。"""
import io, re, os
from PIL import Image

GLYPH_C = r"D:\STM32_Project\SerialAdv_Demo\Drv_Common\glyphs.c"
OUT = r"C:\Users\y7000\WorkBuddy\2026-08-05-21-53-54\verify\oled_preview_demo.png"

W, H = 128, 32
PAGES = H // 8
CELL = 8
COLS = W // CELL
FIRST, LAST = 0x20, 0x7E

src = io.open(GLYPH_C, encoding="utf-8").read()
body = src[src.index("{"):]
font = []
for r in re.findall(r"\{([^{}]*)\}", body):
    v = [int(t, 16) for t in re.findall(r"0x([0-9a-f]{2})", r)]
    if len(v) == 8:
        font.append(v)
assert len(font) == 95, len(font)


class Panel:
    def __init__(self):
        self.pages = [[0] * W for _ in range(PAGES)]

    def blank_row(self, row):
        if row < PAGES:
            self.pages[row] = [0] * W

    def putc(self, col, row, c):
        if col >= COLS or row >= PAGES:
            return
        code = ord(c)
        if code < FIRST or code > LAST:
            c = "?"
            code = ord("?")
        g = font[code - FIRST]
        for x in range(CELL):
            column = 0
            for y in range(8):
                if (g[y] >> (7 - x)) & 1:
                    column |= (1 << y)
            self.pages[row][col * CELL + x] = column

    def puts(self, col, row, s):
        for ch in s:
            if col >= COLS:
                break
            self.putc(col, row, ch)
            col += 1

    def image(self, scale=6):
        img = Image.new("1", (W, H), 0)
        px = img.load()
        for y in range(H):
            for x in range(W):
                if self.pages[y // 8][x] & (1 << (y % 8)):
                    px[x, y] = 1
        return img.resize((W * scale, H * scale), Image.NEAREST)


def render(from_nv, state, text, note):
    p = Panel()
    line = ["N" if not from_nv else "R", " ", "L",
            "1" if state & 1 else "0", " ", "R",
            "1" if state & 2 else "0", " ", "B",
            "1" if state & 4 else "0", " ", "D",
            "1" if state & 8 else "0"]
    p.blank_row(0); p.puts(0, 0, "".join(line))
    padded = (text + " " * 32)[:32]
    p.blank_row(1); p.blank_row(2)
    for i in range(COLS):
        p.putc(i, 1, padded[i])
        p.putc(i, 2, padded[COLS + i])
    p.blank_row(3); p.puts(0, 3, (note + " " * 16)[:16])
    return p, "".join(line)


a, la = render(False, 0x0, "", "NV EMPTY")
b, lb = render(True, 0x5, "HELLO STM32 WORLD", "TEXT SAVED")
print("场景 A 状态行:", repr(la))
print("场景 B 状态行:", repr(lb))

ia, ib = a.image(), b.image()
gap = 24
canvas = Image.new("1", (ia.width, ia.height * 2 + gap), 0)
canvas.paste(ia, (0, 0))
canvas.paste(ib, (0, ia.height + gap))
canvas.save(OUT)
print("saved ->", OUT, canvas.size)

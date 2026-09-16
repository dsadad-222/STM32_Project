# -*- coding: utf-8 -*-
"""把 oled_drv.c 的显存逻辑与 main.c 的排版照抄到 Python，渲染出 OLED 实际会显示的画面。

用途：板子不在手上时验证
  1) 8x8 字模 -> SSD1306 页格式的转置是否正确
  2) 4 行 x 16 字符的排版、行号、状态位是否正确
"""
import io, re, os
from PIL import Image

FONT_C = r"D:\STM32_Project\SerialAdv_Full\Drv_Common\font8x8.c"
OUTDIR = r"C:\Users\y7000\WorkBuddy\2026-08-05-21-53-54\verify"

W, H = 128, 32
PAGES = H // 8
CHAR_W = 8
COL_MAX = W // CHAR_W          # 16
ROW_MAX = PAGES                # 4
FIRST, LAST = 0x20, 0x7E

# ---------- 1. 解析字库 ----------
src = io.open(FONT_C, encoding="utf-8").read()
body = src[src.index("{"):]
rows = re.findall(r"\{([^{}]*)\}", body)
font = []
for r in rows:
    vals = [int(t, 16) for t in re.findall(r"0x([0-9A-Fa-f]{2})", r)]
    if len(vals) == 8:
        font.append(vals)
assert len(font) == LAST - FIRST + 1, f"字库条数不对: {len(font)}"

# ---------- 2. 照抄 oled_drv.c ----------
class Oled:
    def __init__(self):
        self.gram = [[0] * W for _ in range(PAGES)]

    def clear(self):
        self.gram = [[0] * W for _ in range(PAGES)]

    def clear_line(self, row):
        if row >= ROW_MAX:
            return
        self.gram[row] = [0] * W

    def show_char(self, col, row, ch):
        if col >= COL_MAX or row >= ROW_MAX:
            return
        code = ord(ch)
        if code < FIRST or code > LAST:
            ch = "?"
            code = ord("?")
        glyph = font[code - FIRST]
        for col_idx in range(CHAR_W):
            page_byte = 0
            for bit_idx in range(8):
                if glyph[bit_idx] & (0x80 >> col_idx):
                    page_byte |= (1 << bit_idx)
            self.gram[row][col * CHAR_W + col_idx] = page_byte

    def show_string(self, col, row, s):
        for ch in s:
            if col >= COL_MAX:
                break
            self.show_char(col, row, ch)
            col += 1

    def to_image(self, scale=6):
        img = Image.new("1", (W, H), 0)
        px = img.load()
        for y in range(H):
            page = y // 8
            bit = y % 8
            for x in range(W):
                if self.gram[page][x] & (1 << bit):
                    px[x, y] = 1
        return img.resize((W * scale, H * scale), Image.NEAREST)


# ---------- 3. 照抄 main.c 的 UpdateDisplay ----------
def build_frame(boot_restored, left, right, beep, led, text, msg):
    o = Oled()
    line = ["N"] * COL_MAX
    tag = "RST" if boot_restored else "NEW"
    line[0:3] = list(tag)
    line[3] = " "
    line[4] = "L"; line[5] = "1" if left else "0"
    line[6] = " "
    line[7] = "R"; line[8] = "1" if right else "0"
    line[9] = " "
    line[10] = "B"; line[11] = "1" if beep else "0"
    line[12] = " "
    line[13] = "D"; line[14] = "1" if led else "0"
    line[15] = "\0"
    s0 = "".join(line[:15])

    o.clear_line(0); o.show_string(0, 0, s0)

    padded = (text + " " * 32)[:32]
    o.clear_line(1); o.clear_line(2)
    for i in range(COL_MAX):
        o.show_char(i, 1, padded[i])
        o.show_char(i, 2, padded[COL_MAX + i])

    o.clear_line(3); o.show_string(0, 3, msg)
    return o, s0


os.makedirs(OUTDIR, exist_ok=True)

# 场景 A：第一次上电，Flash 里没数据
a, sa = build_frame(False, 0, 0, 0, 0, "", "NO FLASH DATA")
# 场景 B：串口下发 "HELLO FROM SERIAL" 并存盘后，左转+蜂鸣器开着
b, sb = build_frame(True, 1, 0, 1, 1, "HELLO FROM SERIAL", "TEXT SAVED")

print("场景 A 第1行 :", repr(sa), "长度", len(sa))
print("场景 B 第1行 :", repr(sb), "长度", len(sb))
print("场景 A 文本行:", repr(("" + " " * 32)[:32]))
print("场景 B 文本行:", repr(("HELLO FROM SERIAL" + " " * 32)[:32]))

# 把两个场景拼成一张对比图（中间留 24px 白缝）
ia, ib = a.to_image(6), b.to_image(6)
gap = 24
canvas = Image.new("1", (ia.width, ia.height * 2 + gap), 0)
canvas.paste(ia, (0, 0))
canvas.paste(ib, (0, ia.height + gap))
canvas.save(os.path.join(OUTDIR, "oled_preview.png"))
print("saved ->", os.path.join(OUTDIR, "oled_preview.png"), canvas.size)

# 单字符放大图，确认字形没转置错
o = Oled()
o.show_string(0, 0, "AB M5!?~")
o.show_string(0, 1, "0123456789+-*")
o.show_string(0, 2, "abcdefghijklmn")
o.show_string(0, 3, "RST L1 R0 B0 D0")
o.to_image(4).save(os.path.join(OUTDIR, "oled_font_check.png"))
print("saved ->", os.path.join(OUTDIR, "oled_font_check.png"))

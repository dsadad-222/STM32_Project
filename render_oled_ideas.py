# -*- coding: utf-8 -*-
"""
OLED(0.86" 128x32) 玩法预览渲染器。
复用 render_oled_cn.py 的字库与写屏算法（与固件 OLED_ShowChar/Big/CNChar 完全一致），
额外实现 Bresenham 画线/矩形/抖动方块，渲染 6 个玩法场景，
再用 PIL 拼成一张带标签的对比预览图。
"""

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from render_oled_cn import W, H, draw_char8, draw_char_big, draw_cn   # noqa: E402
from PIL import Image, ImageDraw, ImageFont                            # noqa: E402

OUT = r"C:\Users\y7000\Desktop\嵌入式\OLED_玩法预览.png"
SCALE = 4
PANEL_W = W * SCALE
PANEL_H = H * SCALE
ON = (0x8F, 0xDC, 0xFF)      # 蓝色 OLED 像素色
OFF = (0x06, 0x0B, 0x12)


# ---------- 基础绘图（全部按 1 像素粒度操作 128x32 画布） ----------
def px(c, x, y, v=1):
    if 0 <= x < W and 0 <= y < H:
        c[y * W + x] = v


def line(c, x0, y0, x1, y1, v=1):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        px(c, x0, y0, v)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def rect(c, x0, y0, x1, y1, v=1):
    for x in range(x0, x1 + 1):
        px(c, x, y0, v)
        px(c, x, y1, v)
    for y in range(y0, y1 + 1):
        px(c, x0, y, v)
        px(c, x1, y, v)


def fill_rect(c, x0, y0, x1, y1, v=1):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            px(c, x, y, v)


def text8(c, col, row, s):
    for i, ch in enumerate(s):
        if col + i > 15:
            break
        draw_char8(c, col + i, row, ch)


def text8xy(c, x, y, s):
    """按像素坐标写 8x8 文本（x 必须是 8 的倍数对齐，便于与固件一致）"""
    text8(c, x // 8, y // 8, s)


# 2x2 Bayer 有序抖动：把 1 位屏伪装成 4 级灰阶
BAYER = ((0, 2), (3, 1))

def dither_rect(c, x0, y0, x1, y1, level):
    """level 0..4 → 0%/25%/50%/75%/100% 点亮"""
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if BAYER[y & 1][x & 1] < level:
                px(c, x, y)


def invert_rect(c, x0, y0, x1, y1):
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            if 0 <= x < W and 0 <= y < H:
                c[y * W + x] ^= 1


# ---------- 场景 1：滚动波形（示波器） ----------
def scene_wave():
    c = [0] * (W * H)
    text8(c, 0, 0, "T=35.9C AD=1743")
    # 网格：横向虚线 + 纵向刻度点
    for y in (16, 24):
        for x in range(0, 128, 3):
            px(c, x, y)
    for x in (16, 48, 80, 112):
        for y in range(9, 32, 4):
            px(c, x, y)
    # 曲线：缓慢升温 + 轻微噪声（模拟 die 自热）
    pts = []
    for i in range(128):
        t = i / 127.0
        val = 34.5 + 3.4 * t + 0.55 * math.sin(i * 0.42) + 0.22 * math.sin(i * 1.7)
        y = int(round(31 - (val - 33.0) / 8.0 * 22))
        y = max(10, min(31, y))
        pts.append((i, y))
    for i in range(len(pts) - 1):
        line(c, pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1])
    return c


# ---------- 场景 2：模拟指针仪表 ----------
def scene_gauge():
    c = [0] * (W * H)
    cx, cy, r = 64, 31, 25
    # 半圆弧 + 刻度（0V 在左，5V 在右）
    for deg in range(180, -1, -2):
        a = math.radians(deg)
        px(c, int(round(cx + r * math.cos(a))), int(round(cy - r * math.sin(a))))
    for i in range(11):
        a = math.radians(180 - i * 18)
        L = 5 if i % 2 == 0 else 3
        x0 = int(round(cx + (r - L) * math.cos(a)))
        y0 = int(round(cy - (r - L) * math.sin(a)))
        line(c, x0, y0, int(round(cx + r * math.cos(a))), int(round(cy - r * math.sin(a))))
    # 指针（指向 3.9V / 5V 位置）
    val = 3.9 / 5.0
    a = math.radians(180 - val * 180)
    line(c, cx, cy, int(round(cx + (r - 7) * math.cos(a))), int(round(cy - (r - 7) * math.sin(a))))
    # 指针尾部配重 + 轴心
    fill_rect(c, cx - 1, cy - 1, cx + 1, cy)
    # 数字读数（弧外左下安全区）、量程端点标注
    text8xy(c, 0, 24, "3.9V")
    text8xy(c, 112, 24, "5V")
    return c


# ---------- 场景 3：倒车雷达 ----------
def scene_radar():
    c = [0] * (W * H)
    for i, ch in enumerate("32"):
        draw_char_big(c, i, 0, ch)
    text8xy(c, 32, 8, "cm")
    # 右侧 4 段信号条（越高越宽 → 越近越亮），锚在 y=15 往上长
    for i in range(4):
        x0 = 64 + i * 16
        fill_rect(c, x0, 14 - i * 4, x0 + 12, 15, 1 if i < 3 else 0)
    # 危险提示：中文 + 感叹 + 实际距离
    draw_cn(c, 0, 2, "危")
    draw_cn(c, 1, 2, "险")
    text8xy(c, 32, 24, "!!")
    text8xy(c, 64, 24, "0.32m")
    return c


# ---------- 场景 4：中文大字 + 跑马灯 + 打字机光标 ----------
def scene_scroll():
    c = [0] * (W * H)
    text8(c, 0, 0, "SCROLL MSG...")
    msg = "导行视译已就绪"
    for i, ch in enumerate(msg):
        draw_cn(c, i, 1, ch)
    # 末字符被裁掉一半，表现"正在滚动"
    draw_cn(c, len(msg), 1, "请")
    # 底部提示行 + 闪烁方块光标
    text8(c, 0, 3, "KEY2 NEXT   ")
    fill_rect(c, 104, 24, 111, 31)
    return c


# ---------- 场景 5：小游戏（贪吃蛇，三按键可玩） ----------
def scene_game():
    c = [0] * (W * H)
    text8(c, 0, 0, "SCORE 12  HI 30")
    rect(c, 0, 8, 127, 31)
    # 背景点阵
    for y in range(10, 31, 4):
        for x in range(2, 126, 4):
            px(c, x, y)
    # 蛇身（4x4 方块连成的 L 形），蛇头加"眼睛"
    body = [(20, 26), (24, 26), (28, 26), (28, 22), (28, 18), (32, 18), (36, 18), (40, 18), (44, 18)]
    for (x, y) in body:
        fill_rect(c, x, y - 3, x + 3, y)
    fill_rect(c, 21, 24, 22, 25, 0)
    # 食物（十字）
    fx, fy = 96, 22
    line(c, fx - 2, fy, fx + 2, fy)
    line(c, fx, fy - 2, fx, fy + 2)
    return c


# ---------- 场景 6：多级菜单（选中行反白） ----------
def scene_menu():
    c = [0] * (W * H)
    draw_cn(c, 0, 0, "温")
    draw_cn(c, 1, 0, "度")
    text8xy(c, 40, 0, "MONITOR")
    draw_cn(c, 0, 2, "灯")
    draw_cn(c, 1, 2, "光")
    text8xy(c, 40, 16, "LIGHT  ")
    # 选中态：整行反白（黑底白字 → 白底黑字）
    invert_rect(c, 0, 0, 127, 15)
    return c


SCENES = [
    ("① 滚动波形示波器 —— 温度/距离历史曲线", scene_wave),
    ("② 模拟指针仪表 —— 电压/温度表头", scene_gauge),
    ("③ 倒车雷达 —— 距离大字 + 分级警示条", scene_radar),
    ("④ 中文跑马灯 + 打字机光标", scene_scroll),
    ("⑤ 小游戏屏保 —— 三按键可玩的贪吃蛇", scene_game),
    ("⑥ 多级菜单 —— 选中行整行反白", scene_menu),
]


def main():
    cols = 2
    pad = 30
    gap_x, gap_y = 30, 46
    label_h = 30
    title_h = 92
    rows = (len(SCENES) + cols - 1) // cols
    width = pad * 2 + cols * PANEL_W + (cols - 1) * gap_x
    height = title_h + rows * (PANEL_H + label_h + 6) + (rows - 1) * gap_y + 20

    img = Image.new("RGB", (width, height), (0x0B, 0x10, 0x18))
    d = ImageDraw.Draw(img)
    f_title = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 26)
    f_sub = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 16)
    f_lab = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 17)

    d.text((pad, 16), "0.86 寸 OLED（128 x 32）还能怎么玩 —— 真机渲染预览", font=f_title, fill=(0xD8, 0xE8, 0xFF))
    d.text((pad, 46), "全部按固件同一套字库与写屏算法 1:1 渲染，非手绘示意图", font=f_sub, fill=(0x7E, 0x93, 0xAF))

    for idx, (label, fn) in enumerate(SCENES):
        r, col = divmod(idx, cols)
        ox = pad + col * (PANEL_W + gap_x)
        oy = title_h + r * (PANEL_H + label_h + 6 + gap_y)
        # 模块外框（模拟 0.86" 模组的黑色 PCB）
        bez = 7
        d.rounded_rectangle([ox - bez, oy - bez, ox + PANEL_W + bez, oy + PANEL_H + bez],
                            radius=6, fill=(0x04, 0x07, 0x0C), outline=(0x22, 0x31, 0x47))
        d.rectangle([ox, oy, ox + PANEL_W - 1, oy + PANEL_H - 1], fill=OFF)
        canvas = fn()
        for y in range(H):
            for x in range(W):
                if canvas[y * W + x]:
                    d.rectangle([ox + x * SCALE, oy + y * SCALE,
                                 ox + x * SCALE + SCALE - 1, oy + y * SCALE + SCALE - 1], fill=ON)
        d.text((ox, oy + PANEL_H + 12), label, font=f_lab, fill=(0xA8, 0xC2, 0xE0))

    img.save(OUT)
    print("写出：", OUT, img.size)


if __name__ == "__main__":
    main()

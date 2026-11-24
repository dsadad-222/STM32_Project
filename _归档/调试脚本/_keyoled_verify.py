# -*- coding: utf-8 -*-
"""
_keyoled_verify.py —— 从板上 RAM 里读回 OLED 显存，离线渲染出"屏上到底显示什么"

原理：
    oled_drv.c 里的显存是 `static uint8_t s_gram[4][128]`，
    地址已从 KeyOled_Full.axf 的符号表取到：0x2000008C（4 页 x 128 列 = 512 字节）。
    OLED_Refresh() 就是把这 512 字节整屏推给 SSD1306，
    所以"读回 s_gram" == "读回屏上内容"，不依赖人眼看屏。

本机有两套 python，各缺一样东西，所以脚本分两段、互不依赖：
    D:/STM32_AI_Tools/venvs/emb/        有 pyocd，没 Pillow   -> 负责"读"
    C:/Users/y7000/.workbuddy-ai/binaries/python/envs/default/  有 Pillow，没 pyocd -> 负责"渲染"

用法：
    # 第一段：读（pyocd 环境）
    python _keyoled_verify.py --read --dump gram.bin [--reset] [--no-strings]

    # 第二段：渲染（Pillow 环境）
    python _keyoled_verify.py --render gram.bin [--tag poweron]

    # 也支持一步到位（用带 pyocd 的环境，此时不产 PNG）
    python _keyoled_verify.py --read --reset
"""

import argparse
import os
import sys
import time

S_GRAM = 0x2000008C          # fromelf --text -s KeyOled_Full.axf 查得
GRAM_LEN = 512               # 4 页 x 128 列
PAGE_N, OLED_W, OLED_H = 4, 128, 32

UID = "37FF71064E5734360B791543"
TARGET = "stm32f103ze"

CN_NAME_ADDR = 0x08000FFC    # CN_NAME  "李登辉"
CN_CALL_ADDR = 0x08001003    # CN_CALL  "叫爸爸"（= CN_NAME + 7，两个都是 6 字节汉字 + NUL）


# =============================================================================
# 第一段：读显存
# =============================================================================
def connect():
    from pyocd.core.helpers import ConnectHelper

    last = None
    for mode in ("attach", "halt"):
        try:
            s = ConnectHelper.session_with_chosen_probe(
                unique_id=UID, target_override=TARGET, connect_mode=mode,
                options={"auto_unlock": False}, blocking=False)
            s.open()
            print("已连接 (connect_mode=%s)" % mode)
            return s
        except Exception as exc:                                  # noqa: BLE001
            last = exc
            print("connect_mode=%s 失败: %s" % (mode, exc))
    raise SystemExit("连不上调试器: %s" % last)


def do_read(args):
    s = connect()
    t = s.target
    try:
        if args.reset:
            print("复位目标 ...")
            t.reset()
            time.sleep(2.0)          # 等 OLED_Init + 第一屏刷新完成

        if not args.no_strings:
            print("\n固件里的两个字符串（直接读 Flash 常量区核对）：")
            for name, addr in (("CN_NAME", CN_NAME_ADDR), ("CN_CALL", CN_CALL_ADDR)):
                b = bytes(t.read_memory_block8(addr, 7))
                print("  %-8s @0x%08X = %s  ->  %s" % (
                    name, addr, " ".join("%02X" % c for c in b),
                    b[:6].decode("gbk", errors="replace")))

        raw = bytes(t.read_memory_block8(S_GRAM, GRAM_LEN))
    finally:
        s.close()
        print("已断开")

    nonzero = sum(1 for b in raw if b)
    print("\ns_gram @0x%08X  非零字节 = %d / %d" % (S_GRAM, nonzero, GRAM_LEN))
    ascii_dump("屏上实际内容", raw)

    if args.dump:
        with open(args.dump, "wb") as f:
            f.write(raw)
        print("\n显存原始数据已写入: %s" % args.dump)

    if nonzero == 0:
        print("\n!! 显存全 0 —— 要么固件没跑起来，要么 OLED_Refresh 没执行")
        return 1
    print("\n显存非空，屏上确实有内容。")
    return 0


# =============================================================================
# 第二段：渲染（只依赖 Pillow / 纯文本）
# =============================================================================
def ascii_dump(title, raw):
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)
    for y in range(OLED_H):
        page, bit = divmod(y, 8)
        print("".join("#" if (raw[page * OLED_W + x] >> bit) & 1 else "."
                      for x in range(OLED_W)))


def do_render(args):
    raw = open(args.render, "rb").read()
    if len(raw) != GRAM_LEN:
        raise SystemExit("显存 dump 长度不对: %d（应为 %d）" % (len(raw), GRAM_LEN))

    ascii_dump("屏上实际内容  [%s]" % args.tag, raw)

    try:
        from PIL import Image, ImageDraw
    except ImportError:
        print("\n(本环境无 Pillow，只输出 ASCII；要 PNG 请换用带 Pillow 的 python)")
        return 0

    scale, pad, band = 6, 12, 26
    W = pad + OLED_W * scale + pad
    H = pad + band + OLED_H * scale + pad
    img = Image.new("RGB", (W, H), (24, 26, 32))
    d = ImageDraw.Draw(img)
    d.text((pad, pad + 4), "OLED readback: %s" % args.tag, fill=(210, 216, 230))
    ox, oy = pad, pad + band
    d.rectangle([ox - 1, oy - 1, ox + OLED_W * scale, oy + OLED_H * scale],
                outline=(70, 78, 96), fill=(0, 0, 0))
    for page in range(PAGE_N):
        for x in range(OLED_W):
            b = raw[page * OLED_W + x]
            for y in range(8):
                if (b >> y) & 1:
                    px, py = ox + x * scale, oy + (page * 8 + y) * scale
                    d.rectangle([px, py, px + scale - 1, py + scale - 1],
                                fill=(150, 210, 255))
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "_oled_readback_%s.png" % args.tag)
    img.save(out)
    print("\nPNG: %s" % out)
    return 0


# =============================================================================
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--read", action="store_true", help="用 pyocd 从板上读显存")
    ap.add_argument("--reset", action="store_true", help="读之前先复位（看开机第一屏）")
    ap.add_argument("--dump", default=None, help="把 512 字节原始显存写到该文件")
    ap.add_argument("--no-strings", action="store_true", help="跳过 Flash 常量区字符串核对")
    ap.add_argument("--render", default=None, help="渲染一个显存 dump 文件（只依赖 Pillow）")
    ap.add_argument("--tag", default="screen", help="PNG 文件名标签")
    args = ap.parse_args()

    if args.render:
        return do_render(args)
    if args.read:
        return do_read(args)
    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

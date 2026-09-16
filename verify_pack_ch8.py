# -*- coding: utf-8 -*-
"""校验 chapter8 交付 zip：包内源码 == 当前工程源码，且最新功能都在。"""
import hashlib
import zipfile
from pathlib import Path

SRC = Path(r"D:\STM32_Project\AdcTemp_Full")
ZIPS = [
    Path(r"C:\Users\y7000\Desktop\嵌入式\0916_ADC内部温度采集\基于标准库实现ADC内部温度采集.zip"),
    Path(r"C:\Users\y7000\Desktop\嵌入式\0916_ADC内部温度采集\202417010304智能3班陈相林实现ADC内部温度采集.zip"),
]

KEYS = [
    ("App_User/main.c", "s_rainbowIdx"),          # 右转彩虹
    ("App_User/main.c", "RGB2_Set"),
    ("App_User/main.c", "OLED_ShowStringBig"),    # 16px 大字
    ("App_User/main.c", "CN_BOOT_OK"),            # 中文横幅
    ("Drv_Common/led_drv.c", "RGB2_Init"),
    ("Drv_Common/pwm_drv.c", "s_rgbMask"),
    ("Drv_Common/oled_drv.c", "OLED_BIG_DOT_MASK"),
    ("Drv_Common/adc_drv.c", "calOffsetX100"),
    ("App_User/cn_msg.h", "CN_CAL_HINT"),
]


def md5(b):
    return hashlib.md5(b).hexdigest()


for z in ZIPS:
    print("=" * 70)
    print(z.name)
    zf = zipfile.ZipFile(z)
    root = "AdcTemp_Full/"
    # 1. 与工程源码逐字节一致
    diff = []
    for name in ("App_User/main.c", "Drv_Common/led_drv.c", "Drv_Common/pwm_drv.c",
                 "Drv_Common/oled_drv.c", "Drv_Common/adc_drv.c", "App_User/cn_msg.h",
                 "Drv_Common/cn_font16.c"):
        try:
            a = zf.read(root + name)
        except KeyError:
            diff.append((name, "MISSING in zip"))
            continue
        b = (SRC / name).read_bytes()
        if md5(a) != md5(b):
            diff.append((name, "DIFF"))
    print("  源码一致性:", "全部一致" if not diff else diff)
    # 2. hex 一致
    hexin = zf.read(root + "Outputs/AdcTemp_Full.hex")
    hexloc = (SRC / "Project/Objects/AdcTemp_Full.hex").read_bytes()
    print("  hex 一致:", md5(hexin) == md5(hexloc), "size=", len(hexin))
    # 3. 关键功能
    print("  关键功能:")
    for name, key in KEYS:
        try:
            t = zf.read(root + name).decode("utf-8", "ignore")
        except KeyError:
            print("    %-28s ** 文件缺失 **" % name)
            continue
        print("    %-28s %-20s %s" % (name, key, "OK" if key in t else "** MISSING **"))
    # 4. uvprojx 关键设置
    uv = zf.read(root + "Project/AdcTemp_Full.uvprojx").decode("utf-8", "ignore")
    print("  下载范围 -FL07F800:", "OK" if "-FL07F800" in uv else "** MISSING **")
    print("  含 cn_font16.c:", "OK" if "cn_font16.c" in uv else "** MISSING **")
    # 5. 个人信息
    bad = [n for n in zf.namelist() if "uvguix" in n or "y7000" in n]
    print("  个人信息残留:", bad if bad else "无")

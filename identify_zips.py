# -*- coding: utf-8 -*-
"""识别桌面嵌入式目录下各 zip 的真实工程身份（避免按文件名误归类）。"""
import zipfile
from pathlib import Path

D = Path(r"C:\Users\y7000\Desktop\嵌入式")

TARGETS = [
    "202417010304智能3班陈相林实现串口数据控制测试.zip",
    "基于标准库实现串口数据控制测试.zip",
    "202417010304智能3班陈相林实现串口数据控制测试进阶版.zip",
    "基于标准库实现串口数据控制测试进阶版.zip",
]

FEATS = [
    ("OLED 显示", "OLED_Init"),
    ("Flash 存储", "STORE_MAGIC"),
    ("呼吸灯", "Breath_Start"),
    ("中文输出", "\\x"),
    ("转向灯", "TurnSignal"),
    ("ADC 温度", "Adc_"),
]

for name in TARGETS:
    p = D / name
    z = zipfile.ZipFile(p)
    root = sorted({n.split("/")[0] for n in z.namelist()})[0]
    mc = [n for n in z.namelist() if n.endswith("main.c")]
    t = z.read(mc[0]).decode("utf-8", "ignore") if mc else ""
    feats = [k for k, v in FEATS if v in t]
    print(name)
    print("   zip根目录 = %s   文件数 = %d   main.c = %s" % (root, len(z.namelist()), mc[0] if mc else "无"))
    print("   特征 = %s" % ("、".join(feats) if feats else "无"))

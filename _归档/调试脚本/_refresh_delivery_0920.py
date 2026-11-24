# -*- coding: utf-8 -*-
"""刷新 0920 交付副本：重拷源码工程（剔中间产物）+ 更新直接烧录 hex"""
import hashlib
import os
import shutil

SRC = r"D:\STM32_Project\IrAvoid_Full"
BASE = r"C:\Users\y7000\Desktop\嵌入式\0920_红外避障传感器采集"
INNER = os.path.join(BASE, r"202417010304智能3班陈相林实现红外避障传感器采集")
DST_ROOT = os.path.join(INNER, "STM32_Project")
DST = os.path.join(DST_ROOT, "IrAvoid_Full")

EX_DIRS = {"Objects", "Listings"}


def ignore(d, names):
    out = []
    for n in names:
        if n in EX_DIRS or ".uvguix" in n:
            out.append(n)
        elif n.startswith(("build", "flash.log")):
            out.append(n)
        elif n.endswith((".bak", ".map", ".htm", ".lnp")):
            out.append(n)
    return out


if os.path.isdir(DST):
    shutil.rmtree(DST)
os.makedirs(DST_ROOT, exist_ok=True)
shutil.copytree(SRC, DST, ignore=ignore)

tot = 0
for r, ds, fs in os.walk(DST):
    for f in fs:
        tot += os.path.getsize(os.path.join(r, f))

bad = []
for r, ds, fs in os.walk(DST):
    for n in list(ds) + fs:
        if n in EX_DIRS or ".uvguix" in n:
            bad.append(os.path.join(r, n))

# 更新直接烧录 hex
hex_src = os.path.join(SRC, "Project", "Objects", "IrAvoid_Full.hex")
hex_dst = os.path.join(BASE, "红外避障传感器采集_直接烧录.hex")
shutil.copy2(hex_src, hex_dst)


def md5(p):
    h = hashlib.md5()
    with open(p, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 16), b''):
            h.update(chunk)
    return h.hexdigest()


print("工程副本 ->", DST)
print("  体积 = %.2f MB" % (tot / 1048576.0))
print("  残留(应为空) =", bad)
print("  main.c md5 =", md5(os.path.join(DST, "App_User", "main.c")))
print("  源 main.c md5 =", md5(os.path.join(SRC, "App_User", "main.c")))
print("hex ->", hex_dst, os.path.getsize(hex_dst), "bytes  md5 =", md5(hex_dst))

# 确认注释修正已经进交付副本
with open(os.path.join(DST, "App_User", "main.c"), encoding='utf-8', errors='replace') as f:
    s = f.read()
print("  注释已修正 =", "打印两路红外的原始值与引脚分配" in s)
print("  旧注释残留 =", "打印 GPIOA、GPIOF 输入寄存器" in s)

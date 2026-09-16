# -*- coding: utf-8 -*-
"""打包 Reg_Task2_LED / Reg_Task3_Key 为提交用 zip
命名：学号+班级+姓名+代码名称（无 + 号，直接拼接）
"""
import os, zipfile
from pathlib import Path

DESKTOP = Path(r"C:\Users\y7000\Desktop")
ROOT = Path(r"D:\STM32_Project")

# (工程目录, 压缩包名)
PKGS = [
    ("Reg_Task2_LED", "202417010304智能3班陈相林寄存器方式控制IO点亮LED.zip"),
    ("Reg_Task3_Key", "202417010304智能3班陈相林寄存器方式控制按键.zip"),
]

EXCLUDE_NAMES = {".uvguix." + os.getlogin() if False else "",
                 "gen_uvprojx.py", "build_reg.py", "build_both.py",
                 "startup_gnu.s", "stm32f103ze.ld"}
EXCLUDE_NAMES = {"gen_uvprojx.py", "build_reg.py", "build_both.py",
                 "startup_gnu.s", "stm32f103ze.ld"}
EXCLUDE_DIRS = {"Listings", "build", "Objects"}

BAD = ("陈相林", "202417010304", "智能3班", "y7000", "Task1_LED", "StdLib_")

def walk(src, top):
    for dirpath, dirnames, filenames in os.walk(src):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn in EXCLUDE_NAMES:
                continue
            full = Path(dirpath) / fn
            rel = top / full.relative_to(src)
            yield full, rel

def make_zip(proj, zipname):
    src = ROOT / proj
    zpath = DESKTOP / zipname
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for full, rel in walk(src, Path(proj)):
            z.write(full, str(rel).replace("/", "\\"))
    # 泄漏检查
    leak = []
    with zipfile.ZipFile(zpath) as z:
        for n in z.namelist():
            if any(b in n for b in BAD):
                leak.append(("name", n))
            if n.lower().endswith((".c", ".h", ".txt", ".uvprojx", ".uvoptx", ".py", ".ld", ".s")):
                try:
                    txt = z.read(n).decode("utf-8", "ignore")
                except Exception:
                    continue
                for b in BAD:
                    if b in txt:
                        leak.append((b, n.split("\\")[-1]))
    print(f"  {zipname}\n    文件数={len(z.namelist())}  泄漏={leak if leak else 'NONE'}")
    return zpath

if __name__ == "__main__":
    for proj, zname in PKGS:
        make_zip(proj, zname)
    print("\n打包完成 ->", DESKTOP)

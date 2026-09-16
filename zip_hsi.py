# -*- coding: utf-8 -*-
"""打包 StdLib_Task_HSIClock -> 桌面, 命名: 学号+班级+姓名+任务名(无+)"""
import os, zipfile
from pathlib import Path

SRC = Path(r"D:\STM32_Project\StdLib_Task_HSIClock")
DESKTOP = Path(r"C:\Users\y7000\Desktop")
ZIPNAME = "202417010304智能3班陈相林使用HSI配置系统时钟.zip"
OUT = DESKTOP / ZIPNAME

EXCLUDE_NAMES = {".uvguix", "startup_gnu.s", "stm32f103ze.ld", "gen_uvprojx.py"}
EXCLUDE_DIRS = {"Listings", "Objects", "build"}

def walk():
    files = []
    for root, dirs, names in os.walk(SRC):
        # 过滤目录
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        for n in names:
            if n in EXCLUDE_NAMES or n.startswith(".uvguix"):
                continue
            files.append(Path(root) / n)
    return sorted(files)

def main():
    files = walk()
    # 先删旧
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            rel = SRC.name / f.relative_to(SRC)
            z.write(f, str(rel))
    print(f"WROTE {OUT}  ({OUT.stat().st_size} bytes, {len(files)} files)")

if __name__ == "__main__":
    main()

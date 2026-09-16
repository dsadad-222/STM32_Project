# -*- coding: utf-8 -*-
"""打包 chapter4 任务3(DWT) + 任务4(流水灯)，命名: 学号+班级+姓名+任务名 (无+号)"""
import zipfile, os
from pathlib import Path

PKGS = [
    (r"D:\STM32_Project\DWT_Delay",
     r"C:\Users\y7000\Desktop\202417010304智能3班陈相林配置实现DWT延时功能.zip"),
    (r"D:\STM32_Project\FlowingLight",
     r"C:\Users\y7000\Desktop\202417010304智能3班陈相林实现流水灯架构.zip"),
]

EXCLUDE_DIRS = {"Listings", "build", "Objects", "DebugConfig", "__pycache__"}
EXCLUDE_FILES = {".uvguix.y7000", "gen_uvprojx.py", "build.bat", "build_rgb.py",
                 "build_task3.py", "build_both.py", "build_hsi.py", "build_hsi2.py",
                 "build_reg.py", "build_ch4_new.py",
                 "startup_gnu.s", "stm32f103ze.ld"}

def add_dir(zf, root_dir):
    for cur, dirs, files in os.walk(root_dir):
        rel = os.path.relpath(cur, os.path.dirname(root_dir))
        # exclude dirs
        parts = Path(rel).parts
        if any(p in EXCLUDE_DIRS for p in parts):
            dirs[:] = []
            continue
        for f in files:
            if f in EXCLUDE_FILES:
                continue
            full = os.path.join(cur, f)
            arc = os.path.join(Path(root_dir).name, os.path.relpath(full, root_dir))
            zf.write(full, arc)

for src, dst in PKGS:
    src_p = Path(src)
    if os.path.exists(dst): os.remove(dst)
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zf:
        add_dir(zf, str(src_p))
    print(f"[OK] {os.path.basename(dst)}  ({os.path.getsize(dst)} bytes, "
          f"{len(zipfile.ZipFile(dst).namelist())} files)")
print("ALL DONE")

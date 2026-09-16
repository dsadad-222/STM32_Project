# -*- coding: utf-8 -*-
"""打包 chapter4 任务3(DWT) + 任务4(流水灯) 匿名版：仅任务名、无个人信息"""
import zipfile, os
from pathlib import Path

PKGS = [
    (r"D:\STM32_Project\CoreDelay",
     r"C:\Users\y7000\Desktop\配置实现DWT延时功能.zip"),
    (r"D:\STM32_Project\LedPattern",
     r"C:\Users\y7000\Desktop\实现流水灯架构.zip"),
]

EXCLUDE_DIRS = {"Listings", "build", "Objects", "DebugConfig", "__pycache__"}
EXCLUDE_FILES = {".uvguix.y7000", "gen_uvprojx.py", "build.bat",
                 "build_ch4_new.py", "build_ch4_anon.py", "zip_ch4_anon.py",
                 "startup_gnu.s", "stm32f103ze.ld"}

# personal-info strings that must NOT appear anywhere
LEAK_CHECK = ("陈相林", "202417010304", "智能3班", "y7000")

def add_dir(zf, root_dir):
    for cur, dirs, files in os.walk(root_dir):
        rel = os.path.relpath(cur, os.path.dirname(root_dir))
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
    names = zipfile.ZipFile(dst).namelist()
    # leak scan
    leak = []
    for n in names:
        if any(b in n for b in LEAK_CHECK): leak.append(("name", n))
        if n.lower().endswith((".c", ".h", ".txt", ".uvprojx", ".uvoptx", ".py", ".ld", ".s")):
            try:
                t = zipfile.ZipFile(dst).read(n).decode("utf-8", "ignore")
            except Exception:
                continue
            for b in LEAK_CHECK:
                if b in t: leak.append((b, n.split("/")[-1]))
    print(f"[OK] {os.path.basename(dst)}  ({os.path.getsize(dst)} bytes, {len(names)} files)")
    print("     LEAK:", leak if leak else "NONE")

print("ALL DONE")

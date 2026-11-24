# -*- coding: utf-8 -*-
"""打包 SysTick_Tick / TickBlink 为提交用 zip（个人版 + 匿名版）并做泄漏检查"""
import zipfile, os
from pathlib import Path

DESKTOP = Path(r"C:\Users\y7000\Desktop")

PKGS = [
    (r"D:\STM32_Project\SysTick_Tick",
     str(DESKTOP / "202417010304智能3班陈相林实现systick的编程.zip")),
    (r"D:\STM32_Project\TickBlink",
     str(DESKTOP / "实现systick的编程.zip")),
]

EXCLUDE_NAMES = {".uvguix." + "y7000", "gen_uvprojx.py", "build_systick.py"}
EXCLUDE_SUFFIX = (".o", ".d", ".crf", ".axf", ".map", ".htm", ".lnp", ".dep",
                  ".sct", ".lst", ".dbgconf", ".build_log", ".elf")
EXCLUDE_DIRS = {"Listings", "build", "Objects"}

# 真实个人信息，必须零残留（工程名 SysTick_Tick/TickBlink 不算个人信息）
LEAK_CHECK = ("陈相林", "202417010304", "智能3班", "y7000")

def walk(root):
    root = Path(root)
    for p in root.rglob("*"):
        if any(part in EXCLUDE_DIRS for part in p.relative_to(root).parts):
            continue
        if p.is_dir():
            continue
        rel = p.relative_to(root)
        if any(seg.startswith(".uvguix") for seg in rel.parts):
            continue
        if rel.name in EXCLUDE_NAMES:
            continue
        if rel.suffix.lower() in EXCLUDE_SUFFIX:
            continue
        yield p, rel

for root, zippath in PKGS:
    root = Path(root)
    if os.path.exists(zippath):
        os.remove(zippath)
    zf = zipfile.ZipFile(zippath, "w", zipfile.ZIP_DEFLATED)
    n = 0
    for p, rel in walk(root):
        zf.write(p, rel.as_posix())
        n += 1
    zf.close()
    # leak check
    leak = []
    zf = zipfile.ZipFile(zippath)
    for name in zf.namelist():
        if any(b in name for b in LEAK_CHECK):
            leak.append(("name", name))
        if name.lower().endswith((".c", ".h", ".txt", ".uvprojx", ".uvoptx", ".py", ".ld", ".s")):
            try:
                txt = zf.read(name).decode("utf-8", "ignore")
            except Exception:
                continue
            for b in LEAK_CHECK:
                if b in txt:
                    leak.append((b, name.split("/")[-1]))
    print(f"{Path(zippath).name}: {n} files | LEAK: {leak if leak else 'NONE'}")

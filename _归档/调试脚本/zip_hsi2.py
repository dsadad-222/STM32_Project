# -*- coding: utf-8 -*-
"""打包 Task_HSIClock2 -> 桌面 (仅任务名, 无个人信息) 并做残留校验"""
import zipfile
from pathlib import Path

SRC = Path(r"D:\STM32_Project\Task_HSIClock2")
OUT = Path(r"C:\Users\y7000\Desktop\基于标准库使用HSI配置系统时钟.zip")
ROOT = "Task_HSIClock2"

EXCLUDE_DIRS = {"Listings", "build", "Objects"}
EXCLUDE_NAMES = {"gen_uvprojx.py", "startup_gnu.s", "stm32f103ze.ld"}

def keep(p: Path) -> bool:
    if set(p.parts) & EXCLUDE_DIRS:
        return False
    if p.name.startswith(".uvguix"):
        return False
    if p.name in EXCLUDE_NAMES:
        return False
    return True

with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted(SRC.rglob("*")):
        if f.is_dir():
            continue
        rel = f.relative_to(SRC)
        if not keep(rel):
            continue
        z.write(f, f"{ROOT}/{rel.as_posix()}")

print("files:", len(z.namelist()))
print("top:", sorted({n.split("/")[0] for n in z.namelist()}))

# 残留检测
BAD = ("陈相林", "202417010304", "智能3班", "y7000",
       "StdLib_Task_HSIClock", "StdLib_Template", "StdLib_Task3")
leak = []
for n in z.namelist():
    if any(b in n for b in BAD):
        leak.append(("name", n))
    if n.lower().endswith((".c", ".h", ".txt", ".uvprojx", ".uvoptx", ".py", ".ld", ".s")):
        try:
            t = z.read(n).decode("utf-8", "ignore")
        except Exception:
            continue
        for b in BAD:
            if b in t:
                leak.append((b, n.split("/")[-1]))
print("LEAK:", leak if leak else "NONE")
print("main.c:", any(n.endswith("main.c") for n in z.namelist()))
print("OK ->", OUT)

# -*- coding: utf-8 -*-
"""打包两个标准库任务工程为 zip，文件名仅含任务名（无个人信息）。
内部根目录也用任务名；排除编译产物与 GNU 验证辅助文件。"""
import os, zipfile
from pathlib import Path

DESKTOP = Path(r"C:\Users\y7000\Desktop")

PKGS = [
    (Path(r"D:\STM32_Project\Task1_LED"),      "基于标准库实现LED灯的控制"),
    (Path(r"D:\STM32_Project\Task2_KeyRGB"),   "基于标准库实现按键控制LED"),
]

EXCLUDE_NAMES = {".uvguix.y7000", "gen_uvprojx.py", "build_task3.py",
                 "build_both.py", "startup_gnu.s", "stm32f103ze.ld",
                 ".gitignore"}
EXCLUDE_DIRS  = {"Objects", "Listings", "build", "__pycache__"}
SKIP_EXT = {".pyc"}

def should_skip(path: Path, root: Path):
    rel = path.relative_to(root)
    parts = rel.parts
    if parts and parts[0] in EXCLUDE_DIRS:
        return True
    if path.is_file():
        if path.name in EXCLUDE_NAMES:
            return True
        if path.suffix.lower() in SKIP_EXT:
            return True
    return False

def make_zip(root: Path, taskname: str):
    zip_path = DESKTOP / f"{taskname}.zip"
    n = 0
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for cur, dirs, files in os.walk(root):
            curp = Path(cur)
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            for f in files:
                fp = curp / f
                if should_skip(fp, root):
                    continue
                # 跳过空目录本身（zip 不存空目录，这里只处理文件）
                arc = Path(taskname) / fp.relative_to(root)
                z.write(fp, str(arc).replace("/", "\\"))
                n += 1
    print(f"[OK] {zip_path.name}  ({zip_path.stat().st_size} bytes, {n} files)")
    return zip_path

if __name__ == "__main__":
    for root, taskname in PKGS:
        make_zip(root, taskname)
    print("ALL ZIP DONE")

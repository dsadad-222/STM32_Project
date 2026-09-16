# -*- coding: utf-8 -*-
"""核对桌面\嵌入式 总目录：README 里提到的文件是否都在、每项是否齐全。"""
import re
from pathlib import Path

BASE = Path(r"C:\Users\y7000\Desktop\嵌入式")

print("=" * 76)
print("完整目录树")
print("=" * 76)
total = 0
for d in sorted(BASE.iterdir()):
    if d.is_dir():
        files = sorted(f for f in d.rglob("*") if f.is_file())
        total += len(files)
        size = sum(f.stat().st_size for f in files)
        print(f"\n[{d.name}]  {len(files)} 个文件, {size/1024/1024:.2f} MB")
        for f in files:
            rel = f.relative_to(d)
            print(f"    {f.stat().st_size:>9,d}  {rel.as_posix()}")
    else:
        total += 1
        print(f"\n{d.name}  ({d.stat().st_size:,d} B)")
print(f"\n合计 {total} 个文件")

print()
print("=" * 76)
print("README 引用路径核对")
print("=" * 76)
readme = (BASE / "README_总目录说明.md").read_text(encoding="utf-8")
refs = sorted(set(re.findall(r"`([^`]*\\[^`]*)`", readme)))
bad = 0
for r in refs:
    r = r.strip().rstrip("\\")
    if not r or r.startswith(("C:\\\\", "-F")):
        continue
    p = BASE / r
    ok = p.exists()
    if not ok:
        # README 里的相对路径有时省略了所属项目文件夹（如 `预览图\`），
        # 到各项目文件夹下再找一遍，避免误报。
        ok = any(True for _ in BASE.glob("*/" + r))
    if not ok:
        bad += 1
    print(f"  {'OK  ' if ok else 'MISS'}  {r}")
print()
print("引用缺失数:", bad)

print()
print("=" * 76)
print("三件套齐全性检查")
print("=" * 76)
for d in sorted(BASE.iterdir()):
    if not d.is_dir() or d.name.startswith(("_", "00")):
        continue
    names = [f.name for f in d.iterdir()]
    has_src = any(n.endswith(".zip") for n in names)
    has_doc = any(n.endswith(".docx") for n in names)
    has_rep = any("汇报" in n for n in names)
    print(f"  {d.name:32s} 工程包={'Y' if has_src else 'N'}"
          f"  接口文档={'Y' if has_doc else '-'}  汇报稿={'Y' if has_rep else '-'}")

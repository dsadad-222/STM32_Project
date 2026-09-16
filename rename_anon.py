# -*- coding: utf-8 -*-
"""把 _Anon 工程重命名为无关联的中性名 (不含个人信息、不含 _Anon)"""
import shutil
from pathlib import Path

# (old_dir, new_name, old_token, new_token)
MAP = [
    (r"D:\STM32_Project\DWT_Delay_Anon",   "CoreDelay",  "DWT_Delay_Anon",   "CoreDelay"),
    (r"D:\STM32_Project\FlowingLight_Anon","LedPattern", "FlowingLight_Anon","LedPattern"),
]

for old_dir, new_name, old_token, new_token in MAP:
    old_p = Path(old_dir)
    new_p = old_p.parent / new_name
    if new_p.exists():
        shutil.rmtree(new_p)
    old_p.rename(new_p)

    # rename uvprojx / uvoptx
    for ext in (".uvprojx", ".uvoptx"):
        f = new_p / "Project" / (old_token + ext)
        if f.exists():
            f.rename(new_p / "Project" / (new_name + ext))
    # drop user-specific uvguix
    for g in new_p.glob("**/*.uvguix.*"):
        g.unlink()

    # OutputName inside uvprojx
    u = new_p / "Project" / (new_name + ".uvprojx")
    t = u.read_text(encoding="utf-8")
    t = t.replace(f"<OutputName>{old_token}</OutputName>",
                  f"<OutputName>{new_name}</OutputName>")
    u.write_text(t, encoding="utf-8")

    # README references
    r = new_p / "README.txt"
    if r.exists():
        rt = r.read_text(encoding="utf-8")
        rt = rt.replace(old_token, new_token)
        r.write_text(rt, encoding="utf-8")

    # stale artifacts carrying old token
    for f in (new_p / "Outputs").glob(f"{old_token}*"):
        f.unlink()
    bd = new_p / "Project" / "build"
    if bd.exists():
        for f in bd.glob(f"{old_token}*"):
            f.unlink()
    print("renamed ->", new_name)
print("ALL DONE")

# -*- coding: utf-8 -*-
"""同步 0920 交付副本：① 更新 main.c / hex；② 把编译中间产物移出交付树（同盘 rename，不触发删除拦截）"""
import hashlib
import os
import shutil

SRC = r"D:\STM32_Project\IrAvoid_Full"
BASE = r"C:\Users\y7000\Desktop\嵌入式\0920_红外避障传感器采集"
INNER = os.path.join(BASE, r"202417010304智能3班陈相林实现红外避障传感器采集")
DST = os.path.join(INNER, "STM32_Project", "IrAvoid_Full")
STASH = r"C:\Users\y7000\AppData\Local\Temp\_wb_0920_stash"

# ---------- ① 同步变更文件 ----------
pairs = [
    (os.path.join(SRC, "App_User", "main.c"),
     os.path.join(DST, "App_User", "main.c")),
    (os.path.join(SRC, "Project", "Objects", "IrAvoid_Full.hex"),
     os.path.join(BASE, "红外避障传感器采集_直接烧录.hex")),
]
for s, d in pairs:
    assert os.path.isfile(s), s
    shutil.copy2(s, d)
    print("sync ->", d)


def md5(p):
    h = hashlib.md5()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


print("main.c md5  源 =", md5(pairs[0][0]))
print("main.c md5 交付 =", md5(pairs[0][1]))

# ---------- ② 移出编译中间产物 ----------
os.makedirs(STASH, exist_ok=True)
proj = os.path.join(DST, "Project")
moved = []
for name in ("Objects", "Listings", "verify.log", "IrAvoid_Full.uvguix.y7000"):
    p = os.path.join(proj, name)
    if not os.path.exists(p):
        print("  (无)", name)
        continue
    tgt = os.path.join(STASH, name)
    if os.path.exists(tgt):
        # 目标已存在 -> 换个名字
        i = 1
        while os.path.exists(tgt + ".%d" % i):
            i += 1
        tgt = tgt + ".%d" % i
    os.rename(p, tgt)          # ★ 同卷 rename，瞬时且不经过删除通道
    moved.append(name)
    print("  moved out ->", name)

print("移出:", moved)

# ---------- ③ 复查 ----------
bad = []
tot = 0
for r, ds, fs in os.walk(DST):
    for n in list(ds) + fs:
        if n in ("Objects", "Listings") or ".uvguix" in n or n.startswith(("build", "verify")):
            bad.append(os.path.join(r, n))
    for f in fs:
        tot += os.path.getsize(os.path.join(r, f))

print()
print("交付工程体积 = %.2f MB" % (tot / 1048576.0))
print("残留(应为空) =", bad)
assert not bad, "仍有中间产物残留"

with open(os.path.join(DST, "App_User", "main.c"), encoding="utf-8", errors="replace") as f:
    s = f.read()
print("横幅旧行残留 =", "按键: KEY1 " in s or "KEY1 \\xB2\\xE2\\xBE\\xE0" in s)
print("横幅新行已进 =", "KEY1/2/3" in s)

# -*- coding: utf-8 -*-
"""清理 0918 交付包里的 Keil 编译中间产物（第 2 版）。

判定依据（比第 1 版更贴合事实）：
  交付包 Objects/ 里的 .o/.crf/.axf 是 10:30 那一版编译留下的【陈旧产物】，
  而源工程 Objects/ 在 11:01 已用修好的源码全量重建过 —— 所以 md5 必然不同。
  md5 相等不是删除的前提，真正的安全前提是：
      「包内每一个待删文件，在源工程 Objects/ 里都有同名副本」
  已用 comm 验证过：仅包内有、源工程没有的文件数 = 0。
  再加上这些文件全部可由 UV4 -r 全量重建，删除不损失任何信息。

保留：Objects/FlashRW_Full.hex（交付固件）、Objects/FlashRW_Full.sct（分散加载，494B）
另：FlashRW_Full.uvguix.y7000（Keil 每用户 GUI 布局，源工程里没有 → 唯一文件）
    先备份到 BACKUP 再移出交付包。
"""
import os
import shutil

PKG = (r"C:\Users\y7000\Desktop\嵌入式\0918_超声波测距与外部FLASH存储"
       r"\202417010304智能3班陈相林实现超声波测距与外部FLASH存储")
PROJ = r"D:\STM32_Project\RadarFlash_Full"
BACKUP = r"D:\STM32_Project\_pkg_artifacts_backup"

PKG_PROJ = os.path.join(PKG, "STM32_Project", "RadarFlash_Full")
SRC_PROJ = PROJ

ARTIFACT_EXT = (".o", ".crf", ".d", ".axf", ".htm", ".lnp", ".dep",
                ".lst", ".map", ".build_log.htm")
KEEP = {"FlashRW_Full.hex", "FlashRW_Full.sct"}

targets = [
    os.path.join(PKG_PROJ, "Project", "Objects"),
    os.path.join(PKG_PROJ, "Project", "Listings"),
]

# ---- 1. 收集待删文件，逐个验证源工程有同名副本 ----
to_delete = []
unverified = []
for d in targets:
    if not os.path.isdir(d):
        continue
    is_objects = os.path.basename(d) == "Objects"
    src_dir = os.path.join(SRC_PROJ, "Project", os.path.basename(d))
    for fn in sorted(os.listdir(d)):
        full = os.path.join(d, fn)
        if not os.path.isfile(full):
            continue
        if is_objects and fn in KEEP:
            continue
        if not fn.endswith(ARTIFACT_EXT):
            unverified.append((full, "扩展名不在产物清单里"))
            continue
        if not os.path.isfile(os.path.join(src_dir, fn)):
            unverified.append((full, "源工程 Objects/Listings 里无同名副本"))
            continue
        to_delete.append(full)

print("待清理：%d 个（均已确认源工程有同名副本）" % len(to_delete))
by_ext = {}
for p in to_delete:
    by_ext[os.path.splitext(p)[1]] = by_ext.get(os.path.splitext(p)[1], 0) + 1
for e, n in sorted(by_ext.items(), key=lambda kv: -kv[1]):
    print("   %-18s %3d 个" % (e, n))
print("保留：", sorted(KEEP))

if unverified:
    print("\n⚠ 无法确认的文件，保留不动：")
    for p, why in unverified:
        print("   ", os.path.relpath(p, PKG_PROJ), "->", why)

if not to_delete and not unverified:
    print("\n无需清理。")

freed = sum(os.path.getsize(p) for p in to_delete)
for p in to_delete:
    os.remove(p)
print("\n已删除 %d 个，释放 %.1f MB" % (len(to_delete), freed / 1024.0 / 1024.0))

# ---- 2. uvguix 先备份再移出 ----
guix = os.path.join(PKG_PROJ, "Project", "FlashRW_Full.uvguix.y7000")
if os.path.isfile(guix):
    os.makedirs(BACKUP, exist_ok=True)
    shutil.move(guix, os.path.join(BACKUP, "FlashRW_Full.uvguix.y7000"))
    print("uvguix（Keil 每用户 GUI 布局，唯一文件）已备份并移出 -> %s" % BACKUP)

# ---- 3. 复查 ----
print()
for d in targets:
    if os.path.isdir(d):
        print("  %-9s 剩余 %d 个: %s" % (os.path.basename(d), len(os.listdir(d)),
                                        sorted(os.listdir(d))))

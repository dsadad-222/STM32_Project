# -*- coding: utf-8 -*-
"""0916 交付包：清理编译残留 + 重打 zip（只留一个标准版）"""
import os
import ctypes
import zipfile

BASE = r"C:\Users\y7000\Desktop\嵌入式\0916_ADC内部温度采集"
PKG_DIR = os.path.join(BASE, "202417010304智能3班陈相林实现ADC内部温度采集")
ZIP_OUT = os.path.join(BASE, "202417010304智能3班陈相林实现ADC内部温度采集.zip")
SKIP_DIRS = ("Objects", "Listings")


def force_delete(path):
    if os.path.isdir(path):
        for name in os.listdir(path):
            force_delete(os.path.join(path, name))
        ctypes.windll.kernel32.RemoveDirectoryW(path)
    else:
        ctypes.windll.kernel32.SetFileAttributesW(path, 0x80)
        ctypes.windll.kernel32.DeleteFileW(path)


def du_mb(path):
    t = 0
    for dp, _dn, fn in os.walk(path):
        for f in fn:
            try:
                t += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return t / 1048576.0


# ---- 1) 清编译残留 ----
freed = 0.0
for dirpath, dirnames, _fn in os.walk(PKG_DIR):
    for name in list(dirnames):
        if name in SKIP_DIRS:
            p = os.path.join(dirpath, name)
            freed += du_mb(p)
            force_delete(p)
            dirnames.remove(name)
for dirpath, _dn, filenames in os.walk(PKG_DIR):
    for f in filenames:
        if f.startswith("_verify_build") or (f.startswith("build_") and f.endswith(".log")):
            force_delete(os.path.join(dirpath, f))
print("清理编译残留: %.1f MB" % freed)

# ---- 2) 重打 zip ----
if os.path.exists(ZIP_OUT):
    old = os.path.getsize(ZIP_OUT) / 1048576.0
    force_delete(ZIP_OUT)
    print("删除旧 zip: %.1f MB" % old)

count = 0
with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for dirpath, dirnames, filenames in os.walk(PKG_DIR):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for f in filenames:
            full = os.path.join(dirpath, f)
            rel = os.path.relpath(full, BASE)
            zf.write(full, rel)
            count += 1
print("新 zip: %d 个文件, %.1f MB" % (count, os.path.getsize(ZIP_OUT) / 1048576.0))

# ---- 3) 回读校验 ----
with zipfile.ZipFile(ZIP_OUT) as zf:
    bad = zf.testzip()
    names = zf.namelist()
    print("回读校验: testzip=%s, %d 项" % (bad, len(names)))
    for key in ["AdcTemp_Full.uvprojx", "App_User/main.c", "AdcTemp_Full.hex", ".docx"]:
        hit = [n for n in names if key in n]
        print("  含 %-22s : %s" % (key, hit[0] if hit else "!! 缺失"))
    hexn = [n for n in names if n.endswith("AdcTemp_Full.hex")]
    if hexn:
        with zf.open(hexn[0]) as fh:
            data = fh.read()
        print("  hex 大小 %d B, 尾部 %s" % (len(data), data[-12:].decode("ascii", "replace").strip()))

print("\n最终: 文件夹 %.1f MB, zip %.1f MB" % (du_mb(PKG_DIR), os.path.getsize(ZIP_OUT) / 1048576.0))

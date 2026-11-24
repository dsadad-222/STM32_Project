# -*- coding: utf-8 -*-
"""
0916 交付包最终版打包：源码工程 + 接口文档 + 演示视频
顺手清掉误解压产生的同名嵌套副本。
"""
import os
import ctypes
import shutil
import zipfile
from ctypes import wintypes

BASE = r"C:\Users\y7000\Desktop\嵌入式\0916_ADC内部温度采集"
PKG_NAME = "202417010304智能3班陈相林实现ADC内部温度采集"
PKG_DIR = os.path.join(BASE, PKG_NAME)
ZIP_OUT = os.path.join(BASE, PKG_NAME + ".zip")
VIDEO_SRC = r"E:\xwechat_files\wxid_2ffz71i7d1r822_f864\msg\video\2026-09\b71c701e482cd6cfe9045811a14f0a39.mp4"
VIDEO_DST_NAME = "ADC内部温度采集_演示视频.mp4"
SKIP_DIRS = ("Objects", "Listings")


class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND), ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR), ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16), ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p), ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def recycle(paths):
    op = SHFILEOPSTRUCTW()
    op.wFunc = 3
    op.pFrom = "\0".join(paths) + "\0\0"
    op.fFlags = 0x40 | 0x10 | 0x4 | 0x400
    return ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))


def force_delete(path):
    if os.path.isdir(path):
        for n in os.listdir(path):
            force_delete(os.path.join(path, n))
        ctypes.windll.kernel32.RemoveDirectoryW(path)
    else:
        ctypes.windll.kernel32.SetFileAttributesW(path, 0x80)
        ctypes.windll.kernel32.DeleteFileW(path)


def du_mb(p):
    t = 0
    for dp, _dn, fn in os.walk(p):
        for f in fn:
            try:
                t += os.path.getsize(os.path.join(dp, f))
            except OSError:
                pass
    return t / 1048576.0


# ---- 1) 清掉误解压的同名嵌套副本 ----
nested = os.path.join(PKG_DIR, PKG_NAME)
if os.path.isdir(nested):
    print("发现误解压的嵌套副本 (%.1f MB) -> 回收站" % du_mb(nested))
    print("  recycle rc=%d" % recycle([nested]))

# ---- 2) 清编译残留(以防万一) ----
freed = 0.0
for dp, dn, _fn in os.walk(PKG_DIR):
    for name in list(dn):
        if name in SKIP_DIRS:
            p = os.path.join(dp, name)
            freed += du_mb(p)
            force_delete(p)
            dn.remove(name)
if freed:
    print("清理编译残留: %.1f MB" % freed)

# ---- 3) 拷入演示视频 ----
video_dst = os.path.join(PKG_DIR, VIDEO_DST_NAME)
if not os.path.isfile(VIDEO_SRC):
    print("!! 视频源不存在: %s" % VIDEO_SRC)
    raise SystemExit(2)
shutil.copy2(VIDEO_SRC, video_dst)
print("拷入演示视频: %s (%.1f MB)" % (VIDEO_DST_NAME, os.path.getsize(video_dst) / 1048576.0))

# ---- 4) 内容自检 ----
print("\n打包前内容:")
need = [
    ("源码工程 Project", os.path.join(PKG_DIR, "STM32_Project", "AdcTemp_Full", "Project", "AdcTemp_Full.uvprojx")),
    ("源码 App_User", os.path.join(PKG_DIR, "STM32_Project", "AdcTemp_Full", "App_User", "main.c")),
    ("烧录 hex", os.path.join(PKG_DIR, "STM32_Project", "AdcTemp_Full", "Outputs", "AdcTemp_Full.hex")),
    ("接口文档", os.path.join(PKG_DIR, "ADC内部温度采集_接口文档.docx")),
    ("演示视频", video_dst),
]
bad = 0
for label, p in need:
    ok = os.path.isfile(p) and os.path.getsize(p) > 0
    print("  [%s] %-16s %s" % ("OK" if ok else "XX", label, os.path.basename(p)))
    if not ok:
        bad += 1
if bad:
    print("!! 缺项，中止")
    raise SystemExit(3)

# ---- 5) 重打 zip ----
if os.path.exists(ZIP_OUT):
    print("\n删除旧 zip: %.1f MB" % (os.path.getsize(ZIP_OUT) / 1048576.0))
    force_delete(ZIP_OUT)

count = 0
with zipfile.ZipFile(ZIP_OUT, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as zf:
    for dp, dn, fn in os.walk(PKG_DIR):
        dn[:] = [d for d in dn if d not in SKIP_DIRS]
        for f in fn:
            full = os.path.join(dp, f)
            zf.write(full, os.path.relpath(full, BASE))
            count += 1
print("新 zip: %d 个文件, %.1f MB" % (count, os.path.getsize(ZIP_OUT) / 1048576.0))

# ---- 6) 回读校验 ----
with zipfile.ZipFile(ZIP_OUT) as zf:
    print("\n回读校验: testzip=%s, %d 项" % (zf.testzip(), len(zf.namelist())))
    for n in zf.namelist():
        if os.path.splitext(n)[1].lower() in (".mp4", ".docx", ".hex"):
            print("  %-78s %8.1f MB" % (n, zf.getinfo(n).file_size / 1048576.0))
    hexn = [n for n in zf.namelist() if n.endswith("AdcTemp_Full.hex")]
    with zf.open(hexn[0]) as fh:
        tail = fh.read()[-12:].decode("ascii", "replace").strip()
    print("  hex 尾部: %s  (应为 :00000001FF)" % tail)
    uv = [n for n in zf.namelist() if n.endswith(".uvprojx")]
    print("  工程文件: %s" % (uv[0] if uv else "!! 缺失"))

print("\n最终: 文件夹 %.1f MB / zip %.1f MB" % (du_mb(PKG_DIR), os.path.getsize(ZIP_OUT) / 1048576.0))

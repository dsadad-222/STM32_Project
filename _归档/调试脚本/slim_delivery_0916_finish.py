# -*- coding: utf-8 -*-
"""0916 交付包收尾：删 _clean_tmp 副本 + Project 下的编译日志残留"""
import os
import ctypes

ROOT = r"C:\Users\y7000\Desktop\嵌入式\0916_ADC内部温度采集\202417010304智能3班陈相林实现ADC内部温度采集"


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


tmp = os.path.join(ROOT, "_clean_tmp")
if os.path.isdir(tmp):
    print("删除多余副本 _clean_tmp (%.1f MB)" % du_mb(tmp))
    force_delete(tmp)

proj = os.path.join(ROOT, "STM32_Project", "AdcTemp_Full", "Project")
removed = 0
for name in sorted(os.listdir(proj)):
    p = os.path.join(proj, name)
    if name.startswith("build_") and name.endswith(".log"):
        force_delete(p)
        removed += 1
        print("  删除编译日志: " + name)
print("共删除 %d 个日志文件" % removed)

print("\n最终结构:")
for dirpath, dirnames, filenames in os.walk(ROOT):
    depth = dirpath[len(ROOT):].count(os.sep)
    if depth > 2:
        continue
    indent = "  " * depth
    print("%s%s/" % (indent, os.path.basename(dirpath) or ROOT))
    if depth >= 2:
        for f in sorted(filenames)[:6]:
            print("%s  %s" % (indent, f))
print("\n交付包总体积: %.1f MB" % du_mb(ROOT))

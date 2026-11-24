# -*- coding: utf-8 -*-
"""
0916_ADC内部温度采集 交付包瘦身：
保留 = STM32_Project/AdcTemp_Full 源码工程(去掉 Project/Objects、Project/Listings) + 接口文档 docx
其余(33个历史工程 / 散落开发文件 / mp4 / 编译中间产物) 一律清除。

安全策略：
  1) 先把要保留的内容拷到 _clean_tmp，逐项校验
  2) 校验不通过 -> 立即中止，不动原目录一个字节
  3) 校验通过 -> Objects/Listings 永久删除(Keil可重建)，
     其他多余内容走回收站(可恢复)
"""
import os
import sys
import ctypes
import shutil
from ctypes import wintypes

ROOT = r"C:\Users\y7000\Desktop\嵌入式\0916_ADC内部温度采集\202417010304智能3班陈相林实现ADC内部温度采集"
TMP = os.path.join(ROOT, "_clean_tmp")
KEEP_PROJ = "AdcTemp_Full"
SKIP_DIRS = ("Objects", "Listings")


def log(msg):
    print(msg, flush=True)


# ---------- 复制(排除编译中间产物) ----------
def copy_tree(src, dst, skip_names):
    os.makedirs(dst, exist_ok=True)
    for name in os.listdir(src):
        s = os.path.join(src, name)
        d = os.path.join(dst, name)
        if os.path.isdir(s):
            if name in skip_names:
                log("    [跳过] " + name)
                continue
            copy_tree(s, d, skip_names)
        else:
            shutil.copy2(s, d)


# ---------- 永久删除(ctypes, 绕过高层的批量确认) ----------
def force_delete(path):
    if os.path.isdir(path):
        for name in os.listdir(path):
            force_delete(os.path.join(path, name))
        ctypes.windll.kernel32.RemoveDirectoryW(path)
    else:
        ctypes.windll.kernel32.SetFileAttributesW(path, 0x80)  # NORMAL
        ctypes.windll.kernel32.DeleteFileW(path)


# ---------- 回收站删除 ----------
class SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_uint16),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


def recycle(paths):
    if not paths:
        return 0
    FO_DELETE = 3
    FOF_ALLOWUNDO = 0x40
    FOF_NOCONFIRMATION = 0x10
    FOF_SILENT = 0x4
    FOF_NOERRORUI = 0x400
    op = SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = FO_DELETE
    op.pFrom = "\0".join(paths) + "\0\0"
    op.pTo = None
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    return rc


def du_mb(path):
    total = 0
    for dirpath, _dirnames, filenames in os.walk(path):
        for f in filenames:
            try:
                total += os.path.getsize(os.path.join(dirpath, f))
            except OSError:
                pass
    return total / 1048576.0


def main():
    log("源目录: %s" % ROOT)
    before = du_mb(ROOT)
    log("清理前体积: %.1f MB" % before)

    # ===== 步骤1: 拷贝保留内容 =====
    if os.path.exists(TMP):
        log("!! 临时目录已存在，先清掉: %s" % TMP)
        force_delete(TMP)

    src_proj = os.path.join(ROOT, "STM32_Project", KEEP_PROJ)
    if not os.path.isdir(src_proj):
        log("!! 找不到源工程 %s，中止" % src_proj)
        return 2

    log("\n[1/3] 拷贝保留内容 -> _clean_tmp")
    dst_proj = os.path.join(TMP, "STM32_Project", KEEP_PROJ)
    copy_tree(src_proj, dst_proj, SKIP_DIRS)

    keep_docx = None
    for name in os.listdir(ROOT):
        if name.lower().endswith(".docx"):
            keep_docx = name
            shutil.copy2(os.path.join(ROOT, name), os.path.join(TMP, name))
            log("    保留文档: " + name)

    # ===== 步骤2: 校验 =====
    log("\n[2/3] 校验")
    checks = [
        ("App_User/main.c", os.path.join(dst_proj, "App_User", "main.c"), 5000),
        ("App_User/cn_msg.h", os.path.join(dst_proj, "App_User", "cn_msg.h"), 100),
        ("Project/AdcTemp_Full.uvprojx", os.path.join(dst_proj, "Project", "AdcTemp_Full.uvprojx"), 5000),
        ("Outputs/AdcTemp_Full.hex", os.path.join(dst_proj, "Outputs", "AdcTemp_Full.hex"), 20000),
        ("Drv_Common/beep_drv.c", os.path.join(dst_proj, "Drv_Common", "beep_drv.c"), 200),
        ("Drv_Common/oled_drv.c", os.path.join(dst_proj, "Drv_Common", "oled_drv.c"), 500),
        ("Drv_Common/adc_drv.c", os.path.join(dst_proj, "Drv_Common", "adc_drv.c"), 200),
        ("STM32_Library/src", os.path.join(dst_proj, "STM32_Library", "src"), 0),
        ("Startup", os.path.join(dst_proj, "Startup"), 0),
    ]
    bad = 0
    for label, path, minsize in checks:
        if os.path.isdir(path):
            n = len(os.listdir(path))
            ok = n > 0
            log("    %-32s 目录 %d 项  %s" % (label, n, "OK" if ok else "FAIL"))
        elif os.path.isfile(path):
            size = os.path.getsize(path)
            ok = size >= minsize
            log("    %-32s %8d B  %s" % (label, size, "OK" if ok else "FAIL(过小)"))
        else:
            ok = False
            log("    %-32s 缺失  FAIL" % label)
        if not ok:
            bad += 1

    if keep_docx is None:
        log("    docx 缺失 FAIL")
        bad += 1
    else:
        log("    %-32s 已保留" % keep_docx)

    if bad:
        log("\n!! 校验失败 %d 项 —— 已中止，原目录未做任何删除" % bad)
        return 3
    log("    校验全部通过")

    # ===== 步骤3: 清除多余内容 =====
    log("\n[3/3] 清除多余内容")

    # 3a. 编译中间产物 -> 永久删除(Keil 可重建)
    freed = 0.0
    for dirpath, dirnames, _f in os.walk(ROOT):
        for name in list(dirnames):
            if name in SKIP_DIRS:
                p = os.path.join(dirpath, name)
                mb = du_mb(p)
                force_delete(p)
                freed += mb
                dirnames.remove(name)
    log("    永久删除编译中间产物(Objects/Listings): %.1f MB" % freed)

    # 3b. 其余多余内容 -> 回收站(可恢复)
    junk = []
    for name in os.listdir(ROOT):
        if name == "_clean_tmp":
            continue
        p = os.path.join(ROOT, name)
        if name == "STM32_Project":
            for sub in os.listdir(p):
                if sub != KEEP_PROJ:
                    junk.append(os.path.join(p, sub))
        elif keep_docx and name == keep_docx:
            continue
        else:
            junk.append(p)
    rc = recycle(junk)
    log("    移入回收站: %d 项 (SHFileOperation rc=%d)" % (len(junk), rc))

    # 3c. 保留内容移回原位
    dst_root_proj = os.path.join(ROOT, "STM32_Project", KEEP_PROJ)
    if os.path.exists(dst_root_proj):
        log("    !! 目标位置仍存在，跳过移回")
        return 4
    shutil.move(dst_proj, dst_root_proj)
    if keep_docx:
        shutil.move(os.path.join(TMP, keep_docx), os.path.join(ROOT, keep_docx))
    force_delete(TMP)

    after = du_mb(ROOT)
    log("\n=== 完成 ===")
    log("清理前: %.1f MB" % before)
    log("清理后: %.1f MB" % after)
    log("释放:   %.1f MB" % (before - after))
    log("\n最终结构:")
    for name in sorted(os.listdir(ROOT)):
        p = os.path.join(ROOT, name)
        kind = "DIR " if os.path.isdir(p) else "FILE"
        log("  %s %-46s %8.1f MB" % (kind, name, du_mb(p) if os.path.isdir(p) else os.path.getsize(p) / 1048576.0))
    return 0


if __name__ == "__main__":
    sys.exit(main())

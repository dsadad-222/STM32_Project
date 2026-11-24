# -*- coding: utf-8 -*-
"""按内容差异把工程源码同步进 0918 交付包 → 清理编译中间产物 → 重建 zip → 打印 md5。

五步：
  0) sync_renames()   工程文件从 FlashRW_Full.* 改名成 RadarFlash_Full.* 之后，
                       包里的旧名要删掉、新名要补上
                       （sync_sources 只覆盖"同名文件"，处理不了改名）
  1) sync_sources()   只比对源码子目录，按 md5 差异覆盖（不新增文件）
  2) sync_docx()      接口文档成品复制进"含信息包内层"
  3) sync_video()     演示视频复制进"含信息包内层"（源在微信目录，是只读的）
  4) purge_artifacts() 把包内 Objects/Listings 的编译中间产物删掉
                       （保留 Objects/RadarFlash_Full.hex 与 .sct）
                       前置条件：待删文件在源工程同名目录里都有同名副本，
                       否则拒绝删除并列出，避免误删唯一文件
  5) rebuild_zip()    重建 zip（含空目录条目），打印关键文件 md5

⚠ 上一版的坑：只做了 sync_sources，但 zip 是用 os.walk(PKG) 全量打包的。
   包内 Objects/ 里若残留 .o/.crf/.axf（旧版脚本整目录拷贝带进来的），
   就会被一起打进 zip —— 交付包从 377KB 涨到 8.5MB。
   所以清理必须发生在打包之前，且要固化在脚本里。
"""
import hashlib
import os
import shutil
import zipfile

ROOT = r"C:\Users\y7000\Desktop\嵌入式\0918_超声波测距与外部FLASH存储"
PKG_NAME = "202417010304智能3班陈相林实现超声波测距与外部FLASH存储"
PKG = os.path.join(ROOT, PKG_NAME)
ZIP = os.path.join(ROOT, PKG_NAME + ".zip")

PROJ = r"D:\STM32_Project\RadarFlash_Full"
PKG_PROJ = os.path.join(PKG, "STM32_Project", "RadarFlash_Full")
BACKUP = r"D:\STM32_Project\_pkg_artifacts_backup"

# 工程内需要同步的源码子目录（不含 Objects/Listings 等编译产物）
SRC_DIRS = ["App_User", "Drv_Common", "App_Common", "Mid_Common", "Startup",
            "STM32_Library", "Arm_Kernel", "Os", "Doc", "Project"]

HEX_SRC = os.path.join(PROJ, "Project", "Objects", "RadarFlash_Full.hex")
HEX_FLAT = os.path.join(ROOT, "超声波测距与外部FLASH存储_直接烧录.hex")

# 接口文档：成品放在 docs/，要同时进"含信息包内层"和 zip
DOCX_SRC = r"D:\STM32_Project\docs\超声波测距与外部FLASH存储_接口文档.docx"
DOCX_DST = os.path.join(PKG, "超声波测距与外部FLASH存储_接口文档.docx")

# 演示视频：用户从微信发来的录制文件，放进"含信息包内层"顶层（与接口文档并列）
VIDEO_SRC = (r"E:\xwechat_files\wxid_ifph2dohbkn729_0e86\msg\video\2026-09"
             r"\f7bcb3d827a18b66459d14b3b38acc55.mp4")
VIDEO_DST = os.path.join(PKG, "超声波测距与外部FLASH存储_演示视频.mp4")

# ---- 改名同步（2026-09-18）----
# 工程文件原来叫 FlashRW_Full.*（从 0917 隔离副本继承下来的旧名），
# 已统一改成 RadarFlash_Full.*，与文件夹名、任务名一致。
OLD_PREFIX = "FlashRW_Full"
NEW_PREFIX = "RadarFlash_Full"
# 这些文件必须在包里存在，改完名后要主动补进去
RENAME_REQUIRED = [
    ("Project", "uvprojx"),
    ("Project", "uvoptx"),
    (os.path.join("Project", "Objects"), "hex"),
    (os.path.join("Project", "Objects"), "sct"),
]

# ---- 清理规则 ----
ARTIFACT_EXT = (".o", ".crf", ".d", ".axf", ".htm", ".lnp", ".dep",
                ".lst", ".map", ".build_log.htm")
KEEP_IN_OBJECTS = {"RadarFlash_Full.hex", "RadarFlash_Full.sct"}
PURGE_DIRS = ["Objects", "Listings"]
# Keil 每用户 GUI 布局文件：一旦有人用 Keil 打开交付包里的工程就会被自动重建，
# 它不是源码也不是固件，体积却有 ~90KB，不该进交付 zip。
PURGE_GLOB_SUFFIX = (".uvguix.y7000",)


def md5(path):
    h = hashlib.md5()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()


# ---------- 0. 工程文件改名同步 ----------
def sync_renames():
    """包内凡是叫 FlashRW_Full.* 的文件全部删掉，再按新名从源工程补回来。

    为什么不能靠 sync_sources：那个函数只对"包内已存在的同名文件"做 md5 覆盖，
    文件改名后包内根本没有新名，它会走 missing 分支直接跳过，旧名文件则一直留着。
    """
    removed, added = [], []
    for dirpath, _dirs, files in os.walk(PKG_PROJ):
        for fn in files:
            if fn.startswith(OLD_PREFIX):
                p = os.path.join(dirpath, fn)
                os.remove(p)
                removed.append(os.path.relpath(p, PKG_PROJ))
    for sub, ext in RENAME_REQUIRED:
        src = os.path.join(PROJ, sub, "%s.%s" % (NEW_PREFIX, ext))
        dst = os.path.join(PKG_PROJ, sub, "%s.%s" % (NEW_PREFIX, ext))
        if not os.path.exists(src):
            raise SystemExit("改名同步失败：源工程缺 %s" % src)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        added.append(os.path.relpath(dst, PKG_PROJ))

    print("[0/5] 工程改名同步：删除旧名 %d 个，写入新名 %d 个" % (len(removed), len(added)))
    for r in removed:
        print("       - %s" % r)
    for a in added:
        print("       + %s  (%d 字节)" % (a, os.path.getsize(os.path.join(PKG_PROJ, a))))

    # 兜底自检：包内不该再有任何旧名残留
    left = [os.path.relpath(os.path.join(dp, fn), PKG_PROJ)
            for dp, _d, fs in os.walk(PKG_PROJ) for fn in fs
            if fn.startswith(OLD_PREFIX)]
    if left:
        raise SystemExit("改名同步失败：包内仍有旧名残留 %r" % left)
    print("       自检：包内旧名残留 0 处")
    return added


# ---------- 1. 同步源码 ----------
def sync_sources():
    changed, missing = [], []
    for d in SRC_DIRS:
        sdir = os.path.join(PROJ, d)
        if not os.path.isdir(sdir):
            continue
        for dirpath, _dirs, files in os.walk(sdir):
            for fn in files:
                if fn.endswith(ARTIFACT_EXT):
                    continue
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, PROJ)
                dst = os.path.join(PKG_PROJ, rel)
                if not os.path.exists(dst):
                    missing.append(rel)
                    continue
                if md5(src) != md5(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    with open(src, "rb") as fi, open(dst, "wb") as fo:
                        fo.write(fi.read())
                    changed.append(rel)
    print("[1/5] 同步源码：更新 %d 个" % len(changed))
    for c in changed:
        print("      ", c)
    if missing:
        print("      包内缺失、跳过 %d 个（需人工确认是否应新增）：" % len(missing))
        for m in missing:
            print("      ", m)
    return changed


# ---------- 2. 接口文档进包 ----------
def sync_docx():
    """把接口文档 docx 复制进含信息包内层（zip 会一并收进去），并回读校验结构。"""
    if not os.path.exists(DOCX_SRC):
        raise SystemExit("接口文档成品不存在：%s" % DOCX_SRC)
    shutil.copy2(DOCX_SRC, DOCX_DST)
    same = md5(DOCX_SRC) == md5(DOCX_DST)
    with zipfile.ZipFile(DOCX_DST) as z:
        xml = z.read('word/document.xml').decode('utf-8')
    print("[2/5] 接口文档进包：%s" % os.path.basename(DOCX_DST))
    print("      md5 与成品一致：%s" % same)
    print("      结构回读：段落 %d / 表格 %d / 体积 %d 字节"
          % (xml.count('<w:p '), xml.count('<w:tbl>'), os.path.getsize(DOCX_DST)))
    if not same:
        raise SystemExit("接口文档复制后 md5 不一致，中止打包")
    return True


# ---------- 3. 演示视频进包 ----------
def sync_video():
    """把演示视频复制进含信息包内层（zip 会一并收进去），回读校验 md5 + mp4 头。

    ⚠ 微信接收目录里的源文件是**只读**的（-r--r--r--）。用 shutil.copy2 会把只读位
      一起带到目标，之后再想替换/删除就得先 chmod，很别扭；所以这里用 copyfile
      复制内容，再显式把目标权限改回可写。
    """
    if not os.path.exists(VIDEO_SRC):
        raise SystemExit("演示视频源文件不存在：%s" % VIDEO_SRC)
    shutil.copyfile(VIDEO_SRC, VIDEO_DST)
    os.chmod(VIDEO_DST, 0o666)

    same = md5(VIDEO_SRC) == md5(VIDEO_DST)
    with open(VIDEO_DST, "rb") as f:
        head = f.read(12)
    # mp4 的 box 结构：前 4 字节是长度，第 5~8 字节必须是 b'ftyp'
    is_mp4 = head[4:8] == b"ftyp"
    size = os.path.getsize(VIDEO_DST)

    print("[3/5] 演示视频进包：%s" % os.path.basename(VIDEO_DST))
    print("      md5 与源一致：%s" % same)
    print("      mp4 头 ftyp：%s / 体积 %.2f MB (%d 字节)"
          % (is_mp4, size / 1048576.0, size))
    if not same or not is_mp4:
        raise SystemExit("演示视频校验失败，中止打包")
    return True


# ---------- 4. 清理编译产物 ----------
def purge_artifacts():
    removed, unverified = [], []
    for name in PURGE_DIRS:
        d = os.path.join(PKG_PROJ, "Project", name)
        src_dir = os.path.join(PROJ, "Project", name)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            full = os.path.join(d, fn)
            if not os.path.isfile(full):
                continue
            if name == "Objects" and fn in KEEP_IN_OBJECTS:
                continue
            if not fn.endswith(ARTIFACT_EXT):
                unverified.append((full, "扩展名不在产物清单"))
                continue
            if not os.path.isfile(os.path.join(src_dir, fn)):
                unverified.append((full, "源工程同名目录里没有同名副本"))
                continue
            removed.append(full)
    # Keil GUI 布局文件：源工程里通常没有，属"唯一文件"，先备份再移出
    guix_dir = os.path.join(PKG_PROJ, "Project")
    if os.path.isdir(guix_dir):
        for fn in sorted(os.listdir(guix_dir)):
            if fn.endswith(PURGE_GLOB_SUFFIX):
                full = os.path.join(guix_dir, fn)
                os.makedirs(BACKUP, exist_ok=True)
                dst = os.path.join(BACKUP, fn)
                if os.path.exists(dst):
                    os.remove(dst)
                shutil.move(full, dst)
                print("      uvguix（Keil GUI 布局，唯一文件）已备份并移出 -> %s" % BACKUP)
    for p in removed:
        os.remove(p)
    print("[4/5] 清理编译产物：删除 %d 个（源工程留有同名副本，可由 UV4 -r 重建）"
          % len(removed))
    if unverified:
        print("      ⚠ 无法确认来源、保留不动：")
        for p, why in unverified:
            print("      ", os.path.relpath(p, PKG_PROJ), "->", why)
    for name in PURGE_DIRS:
        d = os.path.join(PKG_PROJ, "Project", name)
        if os.path.isdir(d):
            rest = sorted(os.listdir(d))
            print("      %-9s 剩余 %d 个 %s" % (name, len(rest), rest))
    return removed


# ---------- 5. 重建 zip ----------
def rebuild_zip():
    for dst in (os.path.join(PKG_PROJ, "Outputs", "RadarFlash_Full.hex"), HEX_FLAT):
        with open(HEX_SRC, "rb") as fi, open(dst, "wb") as fo:
            fo.write(fi.read())
        print("      hex -> %s  %s" % ("OK" if md5(HEX_SRC) == md5(dst) else "BAD", dst))

    if os.path.exists(ZIP):
        os.remove(ZIP)
    nf = nd = 0
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for dirpath, dirnames, filenames in os.walk(PKG):
            for d in dirnames:
                full = os.path.join(dirpath, d)
                if not os.listdir(full):
                    z.writestr(os.path.relpath(full, ROOT).replace(os.sep, "/") + "/", "")
                    nd += 1
            for fn in filenames:
                full = os.path.join(dirpath, fn)
                z.write(full, os.path.relpath(full, ROOT))
                nf += 1
    print("[5/5] 重建 zip：%d files + %d empty dirs = %d entries, %d bytes"
          % (nf, nd, nf + nd, os.path.getsize(ZIP)))
    with zipfile.ZipFile(ZIP) as z:
        print("      integrity:", "OK" if z.testzip() is None else "BAD")
        for n in z.namelist():
            if n.endswith(("main.c", "led_drv.c", "led_drv.h", ".hex")):
                print("      in-zip %-46s md5=%s"
                      % (os.path.relpath(n, PKG_NAME), hashlib.md5(z.read(n)).hexdigest()))


def verify_zip():
    """zip 内容自检：编译产物 / uvguix 一个都不许有；三件套必须齐全。"""
    bad, names = [], []
    with zipfile.ZipFile(ZIP) as z:
        names = z.namelist()
        if z.testzip() is not None:
            raise SystemExit("zip 完整性校验失败")
        for n in names:
            base = os.path.basename(n)
            if base.endswith(ARTIFACT_EXT):
                bad.append(n)
            if ".uvguix" in base:
                bad.append(n)
            if base.upper() in ("README.MD", "README.TXT"):
                bad.append(n)
    must = {
        "uvprojx": False, "main.c": False, "hcsr04_drv.c": False,
        "docx": False, "hex": False, "mp4": False,
    }
    for n in names:
        b = os.path.basename(n)
        if b.endswith(".uvprojx"):
            must["uvprojx"] = True
        if b == "main.c":
            must["main.c"] = True
        if b == "hcsr04_drv.c":
            must["hcsr04_drv.c"] = True
        if b.endswith(".docx"):
            must["docx"] = True
        if b.endswith(".hex"):
            must["hex"] = True
        if b.endswith(".mp4"):
            must["mp4"] = True
    print("[自检] zip 条目 %d 个，体积 %d 字节 (%.2f MB)"
          % (len(names), os.path.getsize(ZIP), os.path.getsize(ZIP) / 1048576.0))
    print("       编译产物 / uvguix / README 混入：%s"
          % ("无" if not bad else "有 -> %r" % bad[:5]))
    missing = [k for k, v in must.items() if not v]
    print("       必备项：%s"
          % ("齐全（uvprojx / main.c / hcsr04_drv.c / 接口文档 docx / hex / 演示视频 mp4）"
             if not missing else "缺 %r" % missing))

    # 改名自检：包内不该再出现旧工程名 FlashRW_Full
    old = [n for n in names if OLD_PREFIX in os.path.basename(n)]
    newp = sorted({os.path.basename(n) for n in names
                   if os.path.basename(n).startswith(NEW_PREFIX)})
    print("       工程名：旧名 %s / 新名 %d 种 %r"
          % ("残留 -> %r" % old[:5] if old else "无残留", len(newp), newp))

    if bad or missing or old:
        raise SystemExit("交付包自检不通过")


if __name__ == "__main__":
    sync_renames()
    sync_sources()
    sync_docx()
    sync_video()
    purge_artifacts()
    rebuild_zip()
    verify_zip()

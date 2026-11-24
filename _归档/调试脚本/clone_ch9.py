# -*- coding: utf-8 -*-
"""从 AdcTemp_Full 切出 chapter9 新工程 FlashRW_Full"""
import os
import re
import shutil

SRC = r"D:\STM32_Project\AdcTemp_Full"
DST = r"D:\STM32_Project\FlashRW_Full"
OLD = "AdcTemp_Full"
NEW = "FlashRW_Full"

IGNORE_DIRS = {"Objects", "Listings", "build", "__pycache__"}
IGNORE_FILE_PAT = (".log", ".py", ".html", ".uvguix", ".bak", ".map", ".lst", ".crf", ".o", ".d", ".axf", ".htm", ".lnp", ".sct", ".dep")


def ignore(dirpath, names):
    out = []
    for n in names:
        if n in IGNORE_DIRS:
            out.append(n)
            continue
        if any(n.endswith(p) for p in IGNORE_FILE_PAT):
            out.append(n)
    return out


def main():
    if os.path.exists(DST):
        print("!! 目标已存在，先删除: %s" % DST)
        shutil.rmtree(DST)

    shutil.copytree(SRC, DST, ignore=ignore)
    print("复制完成: %s -> %s" % (SRC, DST))

    proj = os.path.join(DST, "Project")

    # 1) 重命名工程文件
    for old_name, new_name in [
        (OLD + ".uvprojx", NEW + ".uvprojx"),
        (OLD + ".uvoptx", NEW + ".uvoptx"),
    ]:
        op = os.path.join(proj, old_name)
        np_ = os.path.join(proj, new_name)
        if os.path.exists(op):
            os.rename(op, np_)
            print("重命名: %s -> %s" % (old_name, new_name))
        else:
            print("!! 找不到 %s" % op)

    # 2) 改 uvprojx：OutputName + 注册 w25q64_drv.c
    up = os.path.join(proj, NEW + ".uvprojx")
    s = open(up, encoding="utf-8", errors="surrogateescape").read()

    n_out = s.count("<OutputName>%s</OutputName>" % OLD)
    s = s.replace("<OutputName>%s</OutputName>" % OLD, "<OutputName>%s</OutputName>" % NEW)
    print("OutputName 替换: %d 处" % n_out)

    # 在 Drv_Common 组末尾插入 w25q64_drv.c
    anchor = "..\\Drv_Common\\pwm_drv.c"
    if "w25q64_drv.c" in s:
        print("w25q64_drv.c 已在工程里，跳过")
    elif anchor in s:
        idx = s.find(anchor)
        end = s.find("</File>", idx) + len("</File>")
        block = ('<File><FileName>w25q64_drv.c</FileName>'
                 '<FileType>1</FileType><FilePath>..\\Drv_Common\\w25q64_drv.c</FilePath></File>')
        s = s[:end] + block + s[end:]
        print("已注册 ..\\Drv_Common\\w25q64_drv.c")
    else:
        print("!! 找不到锚点 %s，需手工加文件" % anchor)

    open(up, "w", encoding="utf-8", errors="surrogateescape").write(s)

    # 3) 顺手删掉 .uvguix（Keil 个人窗口配置）
    for n in os.listdir(proj):
        if ".uvguix" in n:
            os.remove(os.path.join(proj, n))
            print("删除个人配置: %s" % n)

    # 4) 校验
    print("\n=== 校验 ===")
    for f in [NEW + ".uvprojx", NEW + ".uvoptx"]:
        print("  %-28s %s" % (f, "OK" if os.path.exists(os.path.join(proj, f)) else "缺失"))
    print("  OutputName              :", NEW if ("<OutputName>%s</OutputName>" % NEW) in s else "!! 未替换")
    print("  w25q64_drv.c 已注册     :", "OK" if "w25q64_drv.c" in s else "!! 未注册")
    print("\n新工程: %s" % DST)


if __name__ == "__main__":
    main()

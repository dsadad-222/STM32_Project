# -*- coding: utf-8 -*-
"""把克隆来的 RadarFlash_Full 裁剪成 KeyOled_Full：只留 KEY1 + OLED 需要的驱动。

做四件事：
  1) 删掉用不到的驱动源文件（adc/beep/flash/hcsr04/led/pwm/w25q64）
  2) 从 .uvprojx 的 Drv_Common 分组里摘掉对应 <File> 条目
     ⚠ 这些条目有两种排布：多行缩进版 和 挤成一行的单行版，正则必须两种都吃
  3) 重命名 FlashRW_Full.uvprojx/.uvoptx -> KeyOled_Full.*，并改 <OutputName>
  4) 清掉克隆带过来的构建日志与旧名产物
"""
import io
import os
import re
import sys

PROJ_DIR = r"D:\STM32_Project\KeyOled_Full"
OLD = "FlashRW_Full"
NEW = "KeyOled_Full"

# 保留：oled（显示）、key（按键）、systick（时基）、usart（调试打印）、
#       font8x8（ASCII 字模）、cn_font16（中文字模）
KEEP = {"oled_drv", "key_drv", "systick_drv", "usart_drv", "font8x8", "cn_font16"}
ALL_DRV = ["adc_drv", "beep_drv", "cn_font16", "flash_drv", "font8x8", "hcsr04_drv",
           "key_drv", "led_drv", "oled_drv", "pwm_drv", "systick_drv", "usart_drv",
           "w25q64_drv"]
DROP = [d for d in ALL_DRV if d not in KEEP]


def main():
    drv = os.path.join(PROJ_DIR, "Drv_Common")
    removed = []
    for base in DROP:
        for ext in (".c", ".h"):
            p = os.path.join(drv, base + ext)
            if os.path.isfile(p):
                os.remove(p)
                removed.append(base + ext)
    print("[1/4] 删除驱动 %d 个：" % len(removed))
    for r in removed:
        print("      ", r)
    rest = sorted(os.listdir(drv))
    print("      保留：", rest)

    # ---- 2) 摘掉 uvprojx 里的条目 ----
    old_proj = os.path.join(PROJ_DIR, "Project", OLD + ".uvprojx")
    s = io.open(old_proj, encoding="utf-8", errors="ignore").read()

    FILE_RE = re.compile(r'\s*<File>(?:(?!</File>).)*?</File>', re.S)
    name_re = re.compile(r'<FileName>([^<]+)</FileName>')
    drop_names = {d + ".c" for d in DROP}
    dropped = []

    def repl(m):
        fn = name_re.search(m.group(0))
        if fn and fn.group(1) in drop_names:
            dropped.append(fn.group(1))
            return ""
        return m.group(0)

    s = FILE_RE.sub(repl, s)
    print("[2/4] 从 uvprojx 摘掉条目 %d 个：%s" % (len(dropped), sorted(dropped)))
    missing = drop_names - set(dropped)
    if missing:
        sys.exit("有源文件没在 uvprojx 里找到对应条目：%r" % sorted(missing))

    # 确认保留的都还在
    for k in KEEP:
        if ("<FileName>%s.c</FileName>" % k) not in s:
            sys.exit("保留文件 %s.c 的条目丢了！" % k)
    print("      保留条目校验通过：%s" % sorted(KEEP))

    # ---- 3) OutputName ----
    s2, n = re.subn(r'<OutputName>.*?</OutputName>',
                    "<OutputName>%s</OutputName>" % NEW, s, count=1)
    if n != 1:
        sys.exit("OutputName 没替换成功")
    io.open(old_proj, "w", encoding="utf-8", newline="").write(s2)
    print("[3/4] OutputName -> %s" % NEW)

    os.replace(old_proj, os.path.join(PROJ_DIR, "Project", NEW + ".uvprojx"))
    old_opt = os.path.join(PROJ_DIR, "Project", OLD + ".uvoptx")
    if os.path.isfile(old_opt):
        o = io.open(old_opt, encoding="utf-8", errors="ignore").read()
        o = o.replace(OLD, NEW)
        io.open(old_opt, "w", encoding="utf-8", newline="").write(o)
        os.replace(old_opt, os.path.join(PROJ_DIR, "Project", NEW + ".uvoptx"))
    print("      重命名 -> %s.uvprojx / %s.uvoptx" % (NEW, NEW))

    # ---- 4) 清理旧名产物与日志 ----
    junk = []
    for d in ("Project", "Outputs", os.path.join("Project", "Objects"),
              os.path.join("Project", "Listings")):
        full = os.path.join(PROJ_DIR, d)
        if not os.path.isdir(full):
            continue
        for fn in os.listdir(full):
            p = os.path.join(full, fn)
            if not os.path.isfile(p):
                continue
            if (fn.startswith(OLD) or fn.endswith(".log")
                    or fn.endswith(".txt") or ".uvguix" in fn):
                os.remove(p)
                junk.append(os.path.relpath(p, PROJ_DIR))
    print("[4/4] 清理旧名产物/日志 %d 个：%s" % (len(junk), junk))

    print("\n完成。Project/ 内容：")
    for fn in sorted(os.listdir(os.path.join(PROJ_DIR, "Project"))):
        print("   ", fn)


if __name__ == "__main__":
    main()

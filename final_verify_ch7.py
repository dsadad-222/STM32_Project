# -*- coding: utf-8 -*-
"""交付前最终核对：新代码是否进包 + 匿名版是否残留耦合串。"""
import zipfile, os

BASE = r"C:\Users\y7000\Desktop\嵌入式"
INFO = os.path.join(BASE, "202417010304智能3班陈相林实现串口数据控制测试.zip")
ANON = os.path.join(BASE, "基于标准库实现串口数据控制测试.zip")

print("=== [1] 含信息版：PARSE_TAIL 修复是否进包 ===")
z = zipfile.ZipFile(INFO)
src = z.read("SerialCtrl_Full/App_User/main.c").decode("utf-8", "ignore")
print("  含 '避免丢帧' 注释 :", "避免丢帧" in src)
print("  含 byte == FRAME_HEAD0 分支 :", "byte == FRAME_HEAD0" in src)
print("  hex 存在 :", any(n.endswith("SerialCtrl_Full.hex") for n in z.namelist()))
print("  无 README :", not any(n.lower().endswith(("readme.txt", "readme.md")) for n in z.namelist()))

print()
print("=== [2] 匿名版：耦合串自查 ===")
COUPLE = ["陈相林", "202417010304", "智能3班", "SerialCtrl", "key_drv",
          "beep_drv", "usart_drv", "systick_drv", "led_drv", "y7000"]
za = zipfile.ZipFile(ANON)
hits = []
for n in za.namelist():
    for c in COUPLE:
        if c in n:
            hits.append(("name", c, n))
    if n.lower().endswith((".c", ".h", ".txt", ".uvprojx", ".uvoptx", ".s", ".ld", ".py")):
        t = za.read(n).decode("utf-8", "ignore")
        for c in COUPLE:
            if c in t:
                hits.append(("text", c, n))
print("  命中 :", hits if hits else "NONE")
print("  hex 存在 :", any(n.endswith("SerialCmd_Test.hex") for n in za.namelist()))
print("  无 README :", not any(n.lower().endswith(("readme.txt", "readme.md")) for n in za.namelist()))

print()
print("=== [3] 两份源文件清单对照（驱动层命名差异） ===")
for tag, zz in (("info", z), ("anon", za)):
    drv = sorted({n.split("/")[-1] for n in zz.namelist() if n.endswith((".c", ".h")) and "/Drv_Common/" in n})
    print(f"  {tag:5s} Drv_Common -> {drv}")

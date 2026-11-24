# -*- coding: utf-8 -*-
"""进阶版两份 zip 的交付前核对。

重点：
  1) 匿名版里不能出现含信息版独有的命名 / 中文注释 / 个人信息
  2) 两份都含 hex、不含 README、驱动层命名确实不同
"""
import io, os, re, zipfile

BASE = r"C:\Users\y7000\Desktop\嵌入式"
INFO = os.path.join(BASE, "202417010304智能3班陈相林实现串口数据控制测试进阶版.zip")
ANON = os.path.join(BASE, "基于标准库实现串口数据控制测试进阶版.zip")

# 含信息版独有的标识（匿名版里出现任何一个都算耦合）
COUPLE = [
    "陈相林", "202417010304", "智能3班", "y7000",
    "SerialAdv", "SerialCtrl", "SerialCmd",
    "oled_drv", "flash_drv", "font8x8", "led_drv", "beep_drv",
    "systick_drv", "usart_drv", "key_drv",
    "StoreRecord_t", "Store_Save", "Store_Load",
    "OLED_ShowString", "Usart_SendString", "Get_SysRunTime",
    "LED_On", "RGB_Set", "Beep_On",
]

TEXT_EXT = (".c", ".h", ".txt", ".uvprojx", ".uvoptx", ".s", ".ld", ".py", ".md")

print("=" * 70)
print("[1] 含信息版")
print("=" * 70)
zi = zipfile.ZipFile(INFO)
ni = zi.namelist()
print("  文件数 =", len(ni), " 根目录 =", sorted({n.split('/')[0] for n in ni}))
print("  hex    =", [n for n in ni if n.endswith('.hex')])
print("  README =", [n for n in ni if 'readme' in n.lower()] or "无")
src = zi.read("SerialAdv_Full/App_User/main.c").decode("utf-8", "ignore")
print("  含 OLED 驱动调用 :", "OLED_ShowString" in src)
print("  含 Flash 存储调用:", "Store_Save" in src)
print("  含开机恢复逻辑  :", "Store_Load(&rec)" in src)
drv_i = sorted({os.path.basename(n) for n in ni
                if n.endswith(('.c', '.h')) and '/Drv_Common/' in n})
print("  Drv_Common      :", drv_i)

print()
print("=" * 70)
print("[2] 匿名版：耦合串扫描")
print("=" * 70)
za = zipfile.ZipFile(ANON)
na = za.namelist()
print("  文件数 =", len(na), " 根目录 =", sorted({n.split('/')[0] for n in na}))
print("  hex    =", [n for n in na if n.endswith('.hex')])
print("  README =", [n for n in na if 'readme' in n.lower()] or "无")

hits = []
cjk_files = []
for n in na:
    for c in COUPLE:
        if c.lower() in n.lower():
            hits.append(("文件名", c, n))
    if n.lower().endswith(TEXT_EXT):
        t = za.read(n).decode("utf-8", "ignore")
        for c in COUPLE:
            if c.lower() in t.lower():
                hits.append(("内容", c, n))
        # 匿名版应当是纯英文注释
        if re.search(r"[\u4e00-\u9fff]", t):
            cjk_files.append(n)

print("  耦合串命中 :", hits if hits else "NONE")
print("  含中文的文件:", cjk_files if cjk_files else "无（纯英文）")

drv_a = sorted({os.path.basename(n) for n in na
                if n.endswith(('.c', '.h')) and '/Drv_Common/' in n})
print("  Drv_Common  :", drv_a)

print()
print("=" * 70)
print("[3] 两份对照")
print("=" * 70)
print(f"  驱动层命名是否不同 : {set(drv_i) != set(drv_a)}")
print(f"  文件数 {len(ni)} vs {len(na)}")
only_i = sorted(set(drv_i) - set(drv_a))
only_a = sorted(set(drv_a) - set(drv_i))
print("  仅含信息版有 :", only_i)
print("  仅匿名版有   :", only_a)

src_a = za.read("SerialPanel/App_User/main.c").decode("utf-8", "ignore")
print("  匿名版含 panel_show  :", "panel_show" in src_a)
print("  匿名版含 nv_read     :", "nv_read" in src_a)
print("  匿名版含 g_actuators :", "g_actuators" in src_a)

print()
ok = (not hits) and (not cjk_files)
print("最终判定 :", "PASS 匿名版与含信息版无耦合" if ok else "FAIL 需要处理上面的命中项")

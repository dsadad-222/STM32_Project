# -*- coding: utf-8 -*-
import os, glob

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # StdLib_Template
OUT  = os.path.join(BASE, "Project", "StdLib_Template.uvprojx")

# --- 收集 STM32_Library/src 下所有 .c ---
src_dir = os.path.join(BASE, "STM32_Library", "src")
src_files = sorted(os.path.basename(f) for f in glob.glob(os.path.join(src_dir, "*.c")))

def file_block(name, ftype, rel):
    return (f'            <File>\n'
            f'              <FileName>{name}</FileName>\n'
            f'              <FileType>{ftype}</FileType>\n'
            f'              <FilePath>{rel}</FilePath>\n'
            f'            </File>')

groups = []

# Startup
groups.append(("Startup", [
    file_block("startup_stm32f10x_hd.s", 2, r".\Startup\startup_stm32f10x_hd.s"),
]))

# Arm_Kernel
groups.append(("Arm_Kernel", [
    file_block("core_cm3.c", 1, r".\Arm_Kernel\core_cm3.c"),
    file_block("system_stm32f10x.c", 1, r".\Arm_Kernel\system_stm32f10x.c"),
]))

# App_User
groups.append(("App_User", [
    file_block("main.c", 1, r".\App_User\main.c"),
    file_block("stm32f10x_it.c", 1, r".\App_User\stm32f10x_it.c"),
]))

# STM32_Library (仅 .c; .h 通过 IncludePath 引用)
lib_blocks = [file_block(n, 1, r".\STM32_Library\src\\" + n) for n in src_files]
groups.append(("STM32_Library", lib_blocks))

groups_xml = ""
for gname, blocks in groups:
    groups_xml += f'        <Group>\n          <GroupName>{gname}</GroupName>\n          <Files>\n'
    groups_xml += "".join(blocks)
    groups_xml += '          </Files>\n        </Group>\n'

# 读 Task2 模板并替换
tpl_path = r"D:\STM32_Project\Task2\Task2.uvprojx"
with open(tpl_path, encoding="utf-8") as f:
    tpl = f.read()

tpl = tpl.replace("<OutputName>Task2</OutputName>", "<OutputName>StdLib_Template</OutputName>")
# Define (Cads 段)
tpl = tpl.replace("<Define></Define>",
                  "<Define>STM32F10X_HD,USE_STDPERIPH_DRIVER</Define>", 1)
# IncludePath (Cads 段, 仅改第一次出现的空 IncludePath)
tpl = tpl.replace("<IncludePath></IncludePath>",
                  r"<IncludePath>.\Arm_Kernel;.\STM32_Library\inc;.\App_User</IncludePath>", 1)
# 替换 Groups 段（用字符串切片，避开正则转义问题）
gs = tpl.index("<Groups>")
ge = tpl.index("</Groups>") + len("</Groups>")
tpl = tpl[:gs] + "<Groups>\n" + groups_xml + "      </Groups>" + tpl[ge:]

with open(OUT, "w", encoding="utf-8") as f:
    f.write(tpl)

print("已生成:", OUT)
print("STM32_Library 中 .c 文件数:", len(src_files))
print("分组:", [g[0] for g in groups])

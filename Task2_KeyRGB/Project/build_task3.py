# -*- coding: utf-8 -*-
"""
StdLib_Task3 一键编译脚本（GNU ARM Toolchain）
任务2（按键控LED）+ RGB 扩展
学号: 202417010304   班级: 智能3班   姓名: 陈相林
"""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # StdLib_Task3
TOOL = Path(r"C:\Users\y7000\WorkBuddy\2026-08-05-21-53-54\.toolchain\toolchain"
            r"\arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi\bin")
CC   = TOOL / "arm-none-eabi-gcc.exe"
AS   = TOOL / "arm-none-eabi-as.exe"
OC   = TOOL / "arm-none-eabi-objcopy.exe"

BUILD = ROOT / "Project" / "build"
OUT   = ROOT / "Outputs"
BUILD.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

INC = [
    f'-I{ROOT / "Arm_Kernel"}',
    f'-I{ROOT / "STM32_Library" / "inc"}',
    f'-I{ROOT / "App_User"}',
]
CFLAGS = ["-c", "-mcpu=cortex-m3", "-mthumb", "-std=c99", "-Os", "-Wall",
          "-DSTM32F10X_HD", "-DUSE_STDPERIPH_DRIVER",
          "-ffunction-sections", "-fdata-sections"]

def run(cmd, **kw):
    print(" ".join(cmd))
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        raise SystemExit(f"FAIL: {cmd[0]}")

# 编译 main.c
run([str(CC), *CFLAGS, *INC, str(ROOT/"App_User"/"main.c"),
     "-o", str(BUILD/"main.o")])

# 编译 system
run([str(CC), *CFLAGS, *INC, str(ROOT/"Arm_Kernel"/"system_stm32f10x.c"),
     "-o", str(BUILD/"system.o")])

# 编译 it
run([str(CC), *CFLAGS, *INC, str(ROOT/"App_User"/"stm32f10x_it.c"),
     "-o", str(BUILD/"it.o")])

# 编译 STM32_Library/src/*.c
src_dir = ROOT / "STM32_Library" / "src"
for src in sorted(src_dir.glob("*.c")):
    run([str(CC), *CFLAGS, *INC, str(src),
         "-o", str(BUILD / (src.stem + ".o"))])

# 汇编 startup
run([str(AS), "-mcpu=cortex-m3", "-mthumb",
     "-o", str(BUILD/"startup.o"),
     str(ROOT/"Project"/"startup_gnu.s")])

# 链接
objs = [str(p) for p in BUILD.glob("*.o")]
run([str(CC), "-nostartfiles", "-mcpu=cortex-m3", "-mthumb",
     f'-T{ROOT / "Project" / "stm32f103ze.ld"}',
     "-Wl,--gc-sections",
     f'-Wl,-Map={BUILD/"StdLib_Task3.map"}',
     *objs,
     "-o", str(BUILD/"StdLib_Task3.elf")])

# objcopy -> hex
hex_out = OUT / "StdLib_Task3.hex"
run([str(OC), "-O", "ihex",
     str(BUILD/"StdLib_Task3.elf"), str(hex_out)])

print("\n=== DONE ===")
print(f"HEX: {hex_out}")
print(f"SIZE: {hex_out.stat().st_size} bytes")

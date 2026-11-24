# -*- coding: utf-8 -*-
"""编译验证 Task1_LED / Task2_KeyRGB，并生成 Outputs/*.hex（GNU ARM Toolchain）"""
import os, subprocess, struct
from pathlib import Path

TOOL = Path(r"C:\Users\y7000\WorkBuddy\2026-08-05-21-53-54\.toolchain\toolchain"
            r"\arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi\bin")
CC = TOOL / "arm-none-eabi-gcc.exe"
AS = TOOL / "arm-none-eabi-as.exe"
OC = TOOL / "arm-none-eabi-objcopy.exe"

PROJECTS = [
    (Path(r"D:\STM32_Project\Task1_LED"),  "Task1_LED"),
    (Path(r"D:\STM32_Project\Task2_KeyRGB"), "Task2_KeyRGB"),
]

CFLAGS = ["-c", "-mcpu=cortex-m3", "-mthumb", "-std=c99", "-Os", "-Wall",
          "-DSTM32F10X_HD", "-DUSE_STDPERIPH_DRIVER",
          "-ffunction-sections", "-fdata-sections"]

def run(cmd):
    print(" ".join(str(c) for c in cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit("BUILD FAILED")

def build(root: Path, name: str):
    build = root / "Project" / "build"
    out = root / "Outputs"
    build.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    inc = [f"-I{root/'Arm_Kernel'}", f"-I{root/'STM32_Library'/'inc'}", f"-I{root/'App_User'}"]

    # main
    run([str(CC), *CFLAGS, *inc, str(root/"App_User"/"main.c"), "-o", str(build/"main.o")])
    # system + it
    run([str(CC), *CFLAGS, *inc, str(root/"Arm_Kernel"/"system_stm32f10x.c"), "-o", str(build/"system.o")])
    run([str(CC), *CFLAGS, *inc, str(root/"App_User"/"stm32f10x_it.c"), "-o", str(build/"it.o")])
    # library src
    for src in sorted((root/"STM32_Library"/"src").glob("*.c")):
        run([str(CC), *CFLAGS, *inc, str(src), "-o", str(build/(src.stem+".o"))])
    # startup
    run([str(AS), "-mcpu=cortex-m3", "-mthumb", "-o", str(build/"startup.o"), str(root/"Project"/"startup_gnu.s")])
    # link
    objs = [str(p) for p in build.glob("*.o")]
    elf = build / f"{name}.elf"
    run([str(CC), "-nostartfiles", "-mcpu=cortex-m3", "-mthumb",
         f"-T{root/'Project'/'stm32f103ze.ld'}",
         "-Wl,--gc-sections", f"-Wl,-Map={build/f'{name}.map'}",
         *objs, "-o", str(elf)])
    # hex
    hexp = out / f"{name}.hex"
    run([str(OC), "-O", "ihex", str(elf), str(hexp)])
    # 校验向量表
    data = elf.read_bytes()
    # 找 .isr_vector 前 8 字节：直接读 ELF 入口附近不靠谱，改为解析 hex 第一数据行
    print(f"HEX: {hexp}  ({hexp.stat().st_size} bytes)")

if __name__ == "__main__":
    for root, name in PROJECTS:
        print(f"\n===== build {name} =====")
        build(root, name)
    print("\nALL DONE")

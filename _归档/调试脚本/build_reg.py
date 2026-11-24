# -*- coding: utf-8 -*-
"""编译验证 Reg_Task2_LED / Reg_Task3_Key (GNU ARM, 寄存器方式) 并校验向量表"""
import subprocess
from pathlib import Path

TOOL = Path(r"C:\Users\y7000\WorkBuddy\2026-08-05-21-53-54\.toolchain\toolchain"
            r"\arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi\bin")
CC = TOOL / "arm-none-eabi-gcc.exe"
AS = TOOL / "arm-none-eabi-as.exe"
OC = TOOL / "arm-none-eabi-objcopy.exe"

PROJECTS = [r"D:\STM32_Project\Reg_Task2_LED",
            r"D:\STM32_Project\Reg_Task3_Key"]

CFLAGS = ["-c", "-mcpu=cortex-m3", "-mthumb", "-std=c99", "-Os", "-Wall",
          "-DSTM32F10X_HD", "-DUSE_STDPERIPH_DRIVER",
          "-ffunction-sections", "-fdata-sections"]

def run(cmd):
    print("  " + " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd)
    if r.returncode != 0:
        raise SystemExit("BUILD FAILED")

def build(ROOT):
    ROOT = Path(ROOT)
    NAME = ROOT.name
    build = ROOT / "Project" / "build"
    out = ROOT / "Outputs"
    build.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    inc = [f"-I{ROOT/'Arm_Kernel'}", f"-I{ROOT/'STM32_Library'/'inc'}", f"-I{ROOT/'App_User'}"]

    run([str(CC), *CFLAGS, *inc, str(ROOT/"App_User"/"main.c"), "-o", str(build/"main.o")])
    run([str(CC), *CFLAGS, *inc, str(ROOT/"Arm_Kernel"/"system_stm32f10x.c"), "-o", str(build/"system.o")])
    run([str(CC), *CFLAGS, *inc, str(ROOT/"App_User"/"stm32f10x_it.c"), "-o", str(build/"it.o")])
    for src in sorted((ROOT/"STM32_Library"/"src").glob("*.c")):
        run([str(CC), *CFLAGS, *inc, str(src), "-o", str(build/(src.stem+".o"))])
    run([str(AS), "-mcpu=cortex-m3", "-mthumb", "-o", str(build/"startup.o"), str(ROOT/"Project"/"startup_gnu.s")])

    objs = [str(p) for p in build.glob("*.o")]
    elf = build / f"{NAME}.elf"
    run([str(CC), "-nostartfiles", "-mcpu=cortex-m3", "-mthumb",
         f"-T{ROOT/'Project'/'stm32f103ze.ld'}",
         "-Wl,--gc-sections", f"-Wl,-Map={build/f'{NAME}.map'}",
         *objs, "-o", str(elf)])
    hexp = out / f"{NAME}.hex"
    run([str(OC), "-O", "ihex", str(elf), str(hexp)])

    mem = {}
    for line in hexp.read_text().splitlines():
        if not line.startswith(":"):
            continue
        n = int(line[1:3], 16); addr = int(line[3:7], 16); typ = int(line[7:9], 16)
        data = bytes.fromhex(line[9:9+n*2])
        if typ == 4:
            base = int.from_bytes(data, "big") << 16
        elif typ == 0:
            for i, b in enumerate(data):
                mem[base+addr+i] = b
    sp = mem[0x08000000] | mem[0x08000001]<<8 | mem[0x08000002]<<16 | mem[0x08000003]<<24
    rst = mem[0x08000004] | mem[0x08000005]<<8 | mem[0x08000006]<<16 | mem[0x08000007]<<24
    print(f"  HEX: {hexp.name} ({hexp.stat().st_size} bytes)")
    print(f"  Vector -> SP=0x{sp:08X}  Reset_Handler=0x{rst:08X}")
    assert sp == 0x20001000, "SP 异常"
    assert (rst & 0xFF000000) == 0x08000000, "Reset 向量异常"
    print("  BUILD + VERIFY OK\n")

if __name__ == "__main__":
    for p in PROJECTS:
        print("==", p.split("\\")[-1], "==")
        build(p)
    print("ALL DONE")

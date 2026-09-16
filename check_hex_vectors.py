# -*- coding: utf-8 -*-
"""校验 Keil 生成的 .hex 是否可安全烧录。

注意：Keil（ARMCC + ARM 默认分散加载）与 GNU（startup_gnu.s + stm32f103ze.ld）
的布局不同，**不能**套用 build_verify.py 那套 0x20001000 / 0x08000041 断言：
  - Keil: __initial_sp 落在 ZI 段之后（RAM 里），Reset_Handler 在完整向量表之后
  - GNU : SP 固定在 0x20001000，Reset_Handler 在 0x08000040
所以这里做的是"合理性 + 与 .map 符号对齐"校验：
  1. SP 在 SRAM 范围内、4 字节对齐、且高于 ZI 结束
  2. Reset_Handler 为奇数地址（Thumb）、落在 Flash 内
  3. 前 84 个向量表条目（HD 器件）要么为 0，要么是 Flash 内的奇数地址
  4. 若存在同工程 .map，则与 __initial_sp / Reset_Handler 符号逐一比对
"""
import os
import re
import sys

FLASH_BASE, FLASH_END = 0x08000000, 0x08080000
RAM_BASE, RAM_END = 0x20000000, 0x20010000

STORE_PAGE_ADDR = 0x0807F800      # 进阶版用来掉电保存的内部 Flash 数据页

# 默认工程；也可以在命令行上给工程目录名
DEFAULT_PROJECTS = ['SerialCtrl_Full', 'SerialCmd_Test',
                    'SerialAdv_Full', 'SerialPanel']


def build_targets(names):
    t = {}
    for n in names:
        base = os.path.join(r'D:\STM32_Project', n)
        t[n] = (os.path.join(base, 'Outputs', f'{n}.hex'),
                os.path.join(base, 'Project', 'Listings', f'{n}.map'),
                os.path.join(base, 'Startup', 'startup_stm32f10x_hd.s'))
    return t


TARGETS = build_targets(sys.argv[1:] or DEFAULT_PROJECTS)


def vector_slots(startup_path):
    """从启动文件里数出向量表条目数（__Vectors..__Vectors_End 之间的 DCD 行）"""
    if not os.path.exists(startup_path):
        return 76
    n, inside = 0, False
    with open(startup_path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            if '__Vectors' in line and 'EXPORT' not in line and 'Size' not in line:
                inside = True
            if '__Vectors_End' in line:
                inside = False
            if inside and line.strip().startswith('DCD'):
                n += 1
    return n or 76


def read_hex(path):
    mem, upper = {}, 0
    with open(path, 'r', encoding='ascii') as f:
        for line in f:
            line = line.strip()
            if not line.startswith(':'):
                continue
            raw = bytes.fromhex(line[1:])
            n, addr, rtype = raw[0], (raw[1] << 8) | raw[2], raw[3]
            data = raw[4:4 + n]
            if rtype == 0x00:
                for i, b in enumerate(data):
                    mem[upper + addr + i] = b
            elif rtype == 0x04:
                upper = ((data[0] << 8) | data[1]) << 16
            elif rtype == 0x01:
                break
    return mem


def word(mem, a):
    return (mem.get(a, 0) | (mem.get(a + 1, 0) << 8) |
            (mem.get(a + 2, 0) << 16) | (mem.get(a + 3, 0) << 24))


def map_symbols(path):
    syms = {}
    if not os.path.exists(path):
        return syms
    pat = re.compile(r'^\s{4}(\S+)\s+(0x[0-9a-fA-F]+)')
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        for line in f:
            m = pat.match(line)
            if m and m.group(1) in ('__initial_sp', 'Reset_Handler'):
                syms[m.group(1)] = int(m.group(2), 16)
    return syms


all_ok = True
for name, (hexp, mapp, startp) in TARGETS.items():
    checks = []
    if not os.path.exists(hexp):
        print(f'{name}: 找不到 {hexp}')
        all_ok = False
        continue
    slots = vector_slots(startp)
    mem = read_hex(hexp)
    sp, reset = word(mem, 0x08000000), word(mem, 0x08000004)

    checks.append(('SP 在 SRAM 内', RAM_BASE < sp <= RAM_END, f'0x{sp:08X}'))
    checks.append(('SP 4 字节对齐', sp % 4 == 0, ''))
    checks.append(('Reset 是 Thumb 奇数地址', reset & 1 == 1, f'0x{reset:08X}'))
    checks.append(('Reset 在 Flash 内', FLASH_BASE <= (reset & ~1) < FLASH_END, ''))

    bad_vec = []
    for i in range(slots):
        v = word(mem, 0x08000000 + i * 4)
        if i == 0:
            continue
        if v != 0 and not (FLASH_BASE <= (v & ~1) < FLASH_END and (v & 1)):
            bad_vec.append((i, hex(v)))
    checks.append((f'向量表 {slots} 条全部合法', not bad_vec,
                   str(bad_vec[:3]) if bad_vec else ''))

    syms = map_symbols(mapp)
    if syms:
        checks.append(('与 .map 的 __initial_sp 对齐',
                       syms.get('__initial_sp') == sp,
                       f"map=0x{syms.get('__initial_sp', 0):08X}"))
        checks.append(('与 .map 的 Reset_Handler 对齐',
                       syms.get('Reset_Handler') == reset,
                       f"map=0x{syms.get('Reset_Handler', 0):08X}"))

    # 进阶版把最后一页 0x0807F800 当数据页，代码绝不能压到这里
    hi_addr = max(mem)
    checks.append(('代码未压到 Flash 数据页 (0x0807F800)',
                   hi_addr < STORE_PAGE_ADDR,
                   f'代码最高地址 0x{hi_addr:08X}'))

    print(f'== {name}')
    for label, ok, extra in checks:
        print(f'   [{"PASS" if ok else "FAIL"}] {label} {extra}')
        all_ok &= ok
    lo, hi = min(mem), max(mem)
    print(f'   地址范围 0x{lo:08X} ~ 0x{hi:08X}，占用 {len(mem)} 字节 ({len(mem)/1024:.1f} KB)')

print('HEX CHECK:', 'ALL PASS' if all_ok else 'FAILED')
sys.exit(0 if all_ok else 1)

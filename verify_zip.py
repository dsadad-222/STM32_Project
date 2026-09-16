# -*- coding: utf-8 -*-
import zipfile
for name in ['202417010304智能2班陈相林基于标准库实现LED灯的控制.zip', '202417010304智能2班陈相林基于标准库实现按键控制LED.zip']:
    p = 'C:/Users/y7000/Desktop/' + name
    z = zipfile.ZipFile(p)
    names = z.namelist()
    print(f'=== {name[:35]}... ({len(names)} files) ===')
    for n in names[:18]:
        print(f'  {n}')
    if len(names) > 18:
        print(f'  ... ({len(names)-18} more)')
    for kw in ['main.c', '.uvprojx', 'startup_stm32f10x_hd.s', '.hex', 'README.txt']:
        hits = [n for n in names if kw in n]
        if hits:
            print(f'  [OK] {kw}: {hits[0]}')
        else:
            print(f'  [MISS] {kw}')
    print()

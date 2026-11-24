# -*- coding: utf-8 -*-
import zipfile, os
BASE = r"C:\Users\y7000\Desktop\嵌入式"
names = [
    "202417010304智能3班陈相林实现串口数据控制测试.zip",
    "基于标准库实现串口数据控制测试.zip",
]
for nm in names:
    p = os.path.join(BASE, nm)
    z = zipfile.ZipFile(p)
    n = z.namelist()
    print(nm)
    print("  files =", len(n))
    print("  roots =", sorted({x.split("/")[0] for x in n}))
    print("  hex   =", [x for x in n if x.endswith(".hex")])
    info = z.getinfo([x for x in n if x.endswith(".hex")][0]) if any(x.endswith(".hex") for x in n) else None
    if info:
        print("  hex mtime =", info.date_time)
    print()

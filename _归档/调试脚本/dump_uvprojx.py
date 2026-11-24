# -*- coding: utf-8 -*-
"""查看 / 修改 uvprojx 的分组与源文件清单。"""
import re, io, sys

P = r'D:\STM32_Project\SerialAdv_Full\Project\SerialAdv_Full.uvprojx'
s = io.open(P, encoding='utf-8', errors='ignore').read()

print("=== 当前分组 ===")
for g in re.findall(r'<Group>(.*?)</Group>', s, re.S):
    name = re.search(r'<GroupName>(.*?)</GroupName>', g)
    files = re.findall(r'<FileName>(.*?)</FileName>', g)
    print('--', name.group(1) if name else '?')
    for f in files:
        print('     ', f)

print()
print("=== OutputName ===")
print(re.findall(r'<OutputName>(.*?)</OutputName>', s))

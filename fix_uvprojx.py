"""
修复 StdLib_* 工程的 .uvprojx 路径问题：
  源码路径 .\X\  ->  ..\X\   (X 是工程根目录下的子目录)
  OutputDirectory/ListingPath 保持 .\X\ 不变（在 Project/ 子目录下）

适用三个工程：StdLib_Template / StdLib_Task3 / StdLib_Task_RGB
"""
import re, os, sys

# 工程根目录下的子目录（源码层）
SRC_DIRS = ['Startup', 'Arm_Kernel', 'App_User', 'App_Common',
            'Drv_Common', 'Mid_Common', 'Os', 'STM32_Library']

# Keil 编译输出目录（保留 .\）
KEEP_DIRS = ['Objects', 'Listings']

# 三个工程
PROJS = [
    r'D:\STM32_Project\StdLib_Template\Project\StdLib_Template.uvprojx',
    r'D:\STM32_Project\StdLib_Task_RGB\Project\StdLib_Task_RGB.uvprojx',
]

# StdLib_Task3 当前没有 .uvprojx（被我误删了），先重新生成
T3 = r'D:\STM32_Project\StdLib_Task3'
T3_PROJ = os.path.join(T3, 'Project')
T3_UVPROJX = os.path.join(T3_PROJ, 'StdLib_Task3.uvprojx')

# 1) 修复已存在的两个
for path in PROJS:
    if not os.path.isfile(path):
        print(f"  [SKIP] {path} (not found)")
        continue
    content = open(path, encoding='utf-8').read()
    orig = content

    # 1. 源码路径：.\X\ -> ..\X\  （保留 \Objects\ \Listings\）
    pattern = re.compile(r'\.\\(' + '|'.join(SRC_DIRS) + r')\\')
    content = pattern.sub(r'..\\\1\\', content)

    # 2. 防御：再扫一遍 .\<SRC_DIRS> （没有尾随 \ 的场景，如 IncludePath 末尾）
    for d in SRC_DIRS:
        content = content.replace('.\\' + d, '..\\' + d)
        content = content.replace('.\\' + d.lower(), '..\\' + d.lower())

    if content != orig:
        open(path, 'w', encoding='utf-8').write(content)
        print(f"  [FIXED] {path}")
    else:
        print(f"  [OK]    {path} (no change)")

# 2) 重新生成 StdLib_Task3 .uvprojx（基于 StdLib_Template 模板）
print()
print("=== 重新生成 StdLib_Task3 .uvprojx ===")
TPL = r'D:\STM32_Project\StdLib_Template\Project\StdLib_Template.uvprojx'
if os.path.isfile(TPL) and not os.path.isfile(T3_UVPROJX):
    content = open(TPL, encoding='utf-8').read()
    # 改 OutputName
    content = content.replace('StdLib_Template', 'StdLib_Task3')
    # 同样修复路径
    pattern = re.compile(r'\.\\(' + '|'.join(SRC_DIRS) + r')\\')
    content = pattern.sub(r'..\\\1\\', content)
    for d in SRC_DIRS:
        content = content.replace('.\\' + d, '..\\' + d)
        content = content.replace('.\\' + d.lower(), '..\\' + d.lower())
    os.makedirs(T3_PROJ, exist_ok=True)
    open(T3_UVPROJX, 'w', encoding='utf-8').write(content)
    print(f"  [GEN] {T3_UVPROJX}")
else:
    if os.path.isfile(T3_UVPROJX):
        # 已存在，同样修复
        content = open(T3_UVPROJX, encoding='utf-8').read()
        pattern = re.compile(r'\.\\(' + '|'.join(SRC_DIRS) + r')\\')
        content = pattern.sub(r'..\\\1\\', content)
        for d in SRC_DIRS:
            content = content.replace('.\\' + d, '..\\' + d)
        open(T3_UVPROJX, 'w', encoding='utf-8').write(content)
        print(f"  [FIXED] {T3_UVPROJX}")
    else:
        print(f"  [SKIP] template not found: {TPL}")

# 3) 同时修复 .uvoptx（如果有）
print()
print("=== 同步检查 .uvoptx ===")
for optx in [r'D:\STM32_Project\StdLib_Template\Project\StdLib_Template.uvoptx',
             r'D:\STM32_Project\StdLib_Task3\Project\StdLib_Task3.uvoptx',
             r'D:\STM32_Project\StdLib_Task_RGB\Project\StdLib_Task_RGB.uvoptx']:
    if os.path.isfile(optx):
        content = open(optx, encoding='utf-8').read()
        pattern = re.compile(r'\.\\(' + '|'.join(SRC_DIRS) + r')\\')
        new = pattern.sub(r'..\\\1\\', content)
        for d in SRC_DIRS:
            new = new.replace('.\\' + d, '..\\' + d)
        if new != content:
            open(optx, 'w', encoding='utf-8').write(new)
            print(f"  [FIXED] {optx}")
        else:
            print(f"  [OK]    {optx}")
    else:
        print(f"  [N/A]   {optx} (not present)")

print()
print("=== 校验：FilePath 应全部以 ..\\ 开头 ===")
import re
for path in [r'D:\STM32_Project\StdLib_Template\Project\StdLib_Template.uvprojx',
             r'D:\STM32_Project\StdLib_Task3\Project\StdLib_Task3.uvprojx',
             r'D:\STM32_Project\StdLib_Task_RGB\Project\StdLib_Task_RGB.uvprojx']:
    if os.path.isfile(path):
        c = open(path, encoding='utf-8').read()
        fps = re.findall(r'<FilePath>(.*?)</FilePath>', c)
        bad = [f for f in fps if f.startswith('.\\') and not any(f.startswith('.\\' + d) for d in KEEP_DIRS + [''])]
        good = [f for f in fps if f.startswith('..\\')]
        print(f"  {os.path.basename(os.path.dirname(path))}/:")
        print(f"    ..\\ 开头 (正确): {len(good)}")
        print(f"    .\\  开头 (残留): {len(bad)}")
        if bad:
            for b in bad[:5]:
                print(f"      ! {b}")

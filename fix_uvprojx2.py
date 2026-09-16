"""
回滚 + 重新修复：
1. 把被错误变成 `....\X\` 和 `..\X\` 的，统一改成 `..\X\`
2. 再用 negative lookbehind 安全地把 `.\X\` → `..\X\`
"""
import re, os

SRC_DIRS = ['Startup', 'Arm_Kernel', 'App_User', 'App_Common',
            'Drv_Common', 'Mid_Common', 'Os', 'STM32_Library']

PATHS = [
    r'D:\STM32_Project\StdLib_Template\Project\StdLib_Template.uvprojx',
    r'D:\STM32_Project\StdLib_Template\Project\StdLib_Template.uvoptx',
    r'D:\STM32_Project\StdLib_Task3\Project\StdLib_Task3.uvprojx',
    r'D:\STM32_Project\StdLib_Task_RGB\Project\StdLib_Task_RGB.uvprojx',
]

for path in PATHS:
    if not os.path.isfile(path):
        print(f"  [SKIP] {path}")
        continue
    c = open(path, encoding='utf-8').read()
    orig = c

    # 1) 清理 4+ 点的乱码：把任意 N>=2 个点 + 反斜杠开头，强制变回 .\
    c = re.sub(r'\.{2,}\\', r'.\\', c)

    # 2) 现在所有路径都是 .\X\ 形式。用 negative lookbehind 安全转 ..\X\
    #    (?<!\.)  确保前面没有 .
    c = re.sub(
        r'(?<!\.)\.\\(' + '|'.join(SRC_DIRS) + r')\\{1,2}',
        r'..\\\1\\',
        c
    )

    if c != orig:
        open(path, 'w', encoding='utf-8').write(c)
        print(f"  [FIXED] {path}")
    else:
        print(f"  [OK]    {path}")

# 校验
print()
print("=== 校验 ===")
for path in PATHS:
    if not os.path.isfile(path): continue
    c = open(path, encoding='utf-8').read()
    fps = re.findall(r'<FilePath>(.*?)</FilePath>', c)
    good = [f for f in fps if f.startswith('..\\')]
    bad  = [f for f in fps if f.startswith('.\\') and f not in ('.\\Objects\\', '.\\Listings\\')]
    print(f"  {os.path.basename(path)}:")
    print(f"    ..\\ 开头 (对): {len(good)}    .\\ 残留 (错): {len(bad)}")
    if bad:
        for b in bad[:3]:
            print(f"      ! {b}")

"""修复 IncludePath 残留的 .\\X 为 ..\\X"""
import re, os

SRC_DIRS = ['Startup', 'Arm_Kernel', 'App_User', 'App_Common',
            'Drv_Common', 'Mid_Common', 'Os', 'STM32_Library']
PATHS = [
    r'D:\STM32_Project\StdLib_Template\Project\StdLib_Template.uvprojx',
    r'D:\STM32_Project\StdLib_Task3\Project\StdLib_Task3.uvprojx',
    r'D:\STM32_Project\StdLib_Task_RGB\Project\StdLib_Task_RGB.uvprojx',
]

for path in PATHS:
    if not os.path.isfile(path): continue
    c = open(path, encoding='utf-8').read()
    orig = c

    def fix_include(m):
        body = m.group(1)
        for d in SRC_DIRS:
            # 把 .\\d 改成 ..\\d（无论后面跟 ; 还是 \\）
            body = re.sub(r'(?<!\.)\.\\' + d, r'..\\' + d, body)
        return '<IncludePath>' + body + '</IncludePath>'

    c = re.sub(r'<IncludePath>(.*?)</IncludePath>', fix_include, c, flags=re.DOTALL)

    if c != orig:
        open(path, 'w', encoding='utf-8').write(c)
        print(f"  [FIXED] {path}")

# 验证
print()
for path in PATHS:
    if not os.path.isfile(path): continue
    c = open(path, encoding='utf-8').read()
    incs = [i for i in re.findall(r'<IncludePath>(.*?)</IncludePath>', c) if i.strip()]
    print(f"{os.path.basename(os.path.dirname(path))}/: {incs}")

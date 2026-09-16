"""
修复 C/C++ IncludePath 位置错误：
  pos 1728: TargetOption 顶层（汇编器 include path） - 保留
  pos 12473: <Cads>/VariousControls 里的 IncludePath (AC5 C/C++)  - 填入
  pos 13039: <Aads>/VariousControls 里的 IncludePath (AC6 C/C++)  - 填入
"""
import re, os

INC = r'..\Arm_Kernel;..\STM32_Library\inc;..\App_User'
PATHS = [
    r'D:\STM32_Project\StdLib_Template\Project\StdLib_Template.uvprojx',
    r'D:\STM32_Project\StdLib_Task3\Project\StdLib_Task3.uvprojx',
    r'D:\STM32_Project\StdLib_Task_RGB\Project\StdLib_Task_RGB.uvprojx',
]

for path in PATHS:
    if not os.path.isfile(path): continue
    c = open(path, encoding='utf-8').read()
    orig = c

    # 在 <VariousControls>...</VariousControls> 块内，填 <IncludePath>
    def fill_inc(m):
        block = m.group(0)
        if '<IncludePath></IncludePath>' in block:
            return block.replace('<IncludePath></IncludePath>', f'<IncludePath>{INC}</IncludePath>')
        elif '<IncludePath>' in block:
            return block
        else:
            return block.replace('</VariousControls>', f'  <IncludePath>{INC}</IncludePath>\n              </VariousControls>')

    c = re.sub(
        r'<VariousControls>.*?</VariousControls>',
        fill_inc, c, flags=re.DOTALL
    )

    if c != orig:
        open(path, 'w', encoding='utf-8').write(c)
        print(f"  [FIXED] {path}")
    else:
        print(f"  [OK]    {path}")

# 验证
print()
print("=== 校验 ===")
for path in PATHS:
    if not os.path.isfile(path): continue
    c = open(path, encoding='utf-8').read()
    incs = re.findall(r'<IncludePath>(.*?)</IncludePath>', c)
    defs = re.findall(r'<Define>(.*?)</Define>', c)
    print(f"  {os.path.basename(path)}:")
    print(f"    IncludePath 出现 {len(incs)} 次:")
    for i, x in enumerate(incs):
        marker = '✓' if 'Arm_Kernel' in x else '?'
        print(f"      [{marker}] {i+1}: {x[:120]}")
    print(f"    Define 出现 {len(defs)} 次:")
    for i, x in enumerate(defs):
        if x.strip():
            print(f"      [{i+1}] {x}")

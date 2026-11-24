# -*- coding: utf-8 -*-
import re

FUNC_DEF = re.compile(
    r'^\s*(?:static\s+)?(?:const\s+)?'
    r'((?:void|uint8_t|uint16_t|uint32_t|int8_t|int16_t|int32_t|char|float|double|'
    r'uint64_t|int|unsigned\s+char|unsigned\s+int|size_t|KeyEvent|CnGlyph16_t|'
    r'const\s+\w+|\w+_t)\s*\*?)\s+'
    r'(\w+)\s*\(([^;{)]*)\)\s*[{;]',
    re.M)

cases = [
    'const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk);',
    'void OLED_Init(void);',
    'uint8_t Key_Scan(void);',
    'const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk)',
]

for c in cases:
    m = FUNC_DEF.search(c)
    print('%-56s -> %s' % (c[:56], (m.group(1) + ' | ' + m.group(2)) if m else 'NO MATCH'))

print()
src = open(r'D:/STM32_Project/RadarFlash_Full/Drv_Common/cn_font16.h',
           encoding='utf-8', errors='replace').read()
print('全文命中数:', len(FUNC_DEF.findall(src)))
# 逐行试
for i, line in enumerate(src.splitlines(), 1):
    if 'CnFont16_Lookup' in line:
        m = FUNC_DEF.search(line)
        print('第 %d 行: %r' % (i, line))
        print('   匹配:', bool(m), '  ^ 前 8 字符 hex:', line[:8].encode('utf-8').hex())

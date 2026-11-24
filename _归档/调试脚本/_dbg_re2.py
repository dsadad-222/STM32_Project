# -*- coding: utf-8 -*-
import re

PAT = (
    r'^\s*(?:static\s+)?(?:const\s+)?'
    r'((?:void|uint8_t|uint16_t|uint32_t|int8_t|int16_t|int32_t|char|float|double|'
    r'uint64_t|int|unsigned\s+char|unsigned\s+int|size_t|KeyEvent|CnGlyph16_t|'
    r'const\s+\w+|\w+_t)\s*\*?)\s+'
    r'(\w+)\s*\(([^;{)]*)\)\s*[{;]'
)
print('实际模式:')
print(repr(PAT))
print()

s = 'const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk);'

# 逐步拆解
tests = {
    'A 完整': PAT,
    'B 去掉外层可选const': r'^\s*(?:static\s+)?((?:void|CnGlyph16_t|const\s+\w+|\w+_t)\s*\*?)\s+(\w+)\s*\(([^;{)]*)\)\s*[{;]',
    'C 只要const\\s+\\w+': r'^\s*(?:const\s+)?(const\s+\w+\s*\*?)\s+(\w+)\s*\(',
    'D 简化': r'^(const\s+\w+\s*\*?)\s+(\w+)\s*\(([^;{)]*)\)\s*[{;]',
    'E 星号紧贴': r'^\s*(?:const\s+)?(\w+\s*\*)\s*(\w+)\s*\(',
}
for name, p in tests.items():
    m = re.search(p, s)
    print('%-22s -> %s' % (name, m.groups() if m else 'NO MATCH'))

# -*- coding: utf-8 -*-
"""
audit_docx.py —— 接口文档结构审计

输出：
  1. 全部标题（按出现顺序），带层级缩进
  2. 章节编号连续性检查（跳号 / 重号 / 断号）
  3. 每张表的表头 + 行数
  4. 关键词残留扫描（旧引脚、旧功能名、占位符）
"""

import re
import sys
from collections import Counter

from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
NS = {'w': W[1:-1]}


def qn(t):
    return W + t


def ptext(p):
    return ''.join(t.text or '' for t in p.iter(qn('t')))


def style_of(p):
    pPr = p.find(qn('pPr'))
    if pPr is None:
        return ''
    ps = pPr.find(qn('pStyle'))
    if ps is None:
        return ''
    return ps.get(qn('val')) or ''


def is_heading(p):
    st = style_of(p)
    return st.startswith('Heading') or st.startswith('heading') or re.match(r'^\d$', st or '')


def body_of(docx):
    with open(docx, 'rb') as f:
        import zipfile
        with zipfile.ZipFile(f) as z:
            return etree.fromstring(z.read('word/document.xml'))


def main(path):
    root = body_of(path)
    body = root.find(qn('body'))

    print('=' * 78)
    print('文档结构审计: %s' % path)
    print('=' * 78)

    headings = []
    tables = []
    for el in body:
        tag = etree.QName(el).localname
        if tag == 'p':
            txt = ptext(el).strip()
            if txt and is_heading(el):
                headings.append((style_of(el), txt))
        elif tag == 'tbl':
            rows = el.findall(qn('tr'))
            hdr = []
            if rows:
                for tc in rows[0].findall(qn('tc')):
                    hdr.append(ptext(tc).strip())
            tables.append((hdr, len(rows)))

    print('\n---- 标题清单 (%d 条) ----' % len(headings))
    for st, t in headings:
        lvl = ''.join(ch for ch in st if ch.isdigit())
        depth = int(lvl) if lvl.isdigit() else 1
        print('%s%s   [%s]' % ('    ' * max(0, depth - 1), t, st))

    # ---- 编号连续性 ----
    print('\n---- 章节编号连续性 ----')
    nums = []
    for _, t in headings:
        m = re.match(r'^(\d+(?:\.\d+)*)\s', t)
        if m:
            nums.append(m.group(1))

    problems = []
    seen = Counter(nums)
    for n, c in seen.items():
        if c > 1:
            problems.append('重号: %s 出现 %d 次' % (n, c))

    # 同级递增检查：按父节点分组
    from collections import defaultdict
    groups = defaultdict(list)
    for n in nums:
        parts = n.split('.')
        groups['.'.join(parts[:-1])].append(int(parts[-1]))
    for parent, kids in groups.items():
        kids_sorted = sorted(kids)
        expect = list(range(1, len(kids_sorted) + 1))
        if kids_sorted != expect:
            problems.append('父节 %r 的子号是 %s（期望 1..%d）'
                            % (parent or '(顶级)', kids_sorted, len(kids_sorted)))

    if problems:
        for p in problems:
            print('  !! %s' % p)
    else:
        print('  OK: 编号连续，无跳号/重号')

    print('\n---- 表格清单 (%d 张) ----' % len(tables))
    for i, (hdr, n) in enumerate(tables, 1):
        h = ' | '.join(x[:14] for x in hdr[:5])
        print('  %2d. %2d 行  表头: %s' % (i, n, h))

    # ---- 关键词扫描 ----
    allt = '\n'.join(ptext(e) for e in body.iter(qn('p')))
    for tbl in body.iter(qn('tbl')):
        allt += '\n' + '\n'.join(ptext(tc) for tc in tbl.iter(qn('tc')))

    print('\n---- 关键词扫描 ----')
    checks = [
        ('PG0', '旧引脚 PG0（应已全部改掉）'),
        ('PG1（左灯珠红色通道）', '新引脚写法'),
        ('PE7', '左灯珠绿通道'),
        ('待补充', '占位符'),
        ('TODO', '占位符'),
        ('XXX', '占位符'),
        ('???', '占位符'),
        ('超声波', '任务4 关键词'),
        ('HC-SR04', '任务4 关键词'),
        ('W25Q64', '外部 FLASH'),
        ('距离记录', '任务4 关键词'),
    ]
    for kw, desc in checks:
        n = allt.count(kw)
        flag = '!!' if (kw in ('PG0', '待补充', 'TODO', 'XXX', '???') and n > 0) else '  '
        print('  %s %-24s %3d 次   %s' % (flag, kw, n, desc))

    print('\n段落总数 = %d   表格总数 = %d'
          % (sum(1 for e in body.iter(qn('p'))), len(tables)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1]))

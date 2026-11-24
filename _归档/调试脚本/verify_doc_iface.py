# -*- coding: utf-8 -*-
"""
verify_doc_iface.py —— 把接口文档里写明的函数原型，逐个跟真实源码对账

做法：
  1. 从 docx 里抽出所有"函数原型"表第二列 -> 文档声称的接口
  2. 逐行扫描工程所有 .c / .h，识别函数声明/定义行 -> 真实接口
  3. 按函数名对齐，归一化空白后逐字符比对签名

为什么用逐行解析而不是一个巨型正则：
  `const CnGlyph16_t *CnFont16_Lookup(uint16_t gbk);` 这种"const 类型 *函数名"的写法
  会让 `(?:const\\s+)?` 和 `const\\s+\\w+` 两条分支互相打架，正则回溯行为很难预期
  （实测会漏匹配）。逐行取"第一个左括号前的最后一个标识符"最稳。
"""

import os
import re
import sys
import zipfile

from lxml import etree

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'


def qn(t):
    return W + t


def ptext(e):
    return ''.join(t.text or '' for t in e.iter(qn('t')))


# ---------------------------------------------------------------------------
# 1. 文档侧
# ---------------------------------------------------------------------------
def doc_prototypes(docx):
    """返回 [(章节标题, 原型文本)]"""
    with zipfile.ZipFile(docx) as z:
        root = etree.fromstring(z.read('word/document.xml'))
    body = root.find(qn('body'))

    out = []
    last_heading = ''
    for el in body:
        tag = etree.QName(el).localname
        if tag == 'p':
            t = ptext(el).strip()
            pPr = el.find(qn('pPr'))
            st = ''
            if pPr is not None:
                ps = pPr.find(qn('pStyle'))
                if ps is not None:
                    st = ps.get(qn('val')) or ''
            if t and st:
                last_heading = t
        elif tag == 'tbl':
            rows = el.findall(qn('tr'))
            if not rows:
                continue
            hdr = [ptext(tc).strip() for tc in rows[0].findall(qn('tc'))]
            # 四行一表：| 函数原型 | <原型> | / | 描述 | ... | / | 参数 | ... | / | 返回值 | ... |
            if hdr and hdr[0] == '函数原型':
                for r in rows:
                    tcs = r.findall(qn('tc'))
                    if len(tcs) >= 2 and ptext(tcs[0]).strip() == '函数原型':
                        proto = ptext(tcs[1]).strip()
                        if proto and '(' in proto:
                            out.append((last_heading, proto))
    return out


# ---------------------------------------------------------------------------
# 2. 源码侧
# ---------------------------------------------------------------------------
WS = re.compile(r'\s+')
NAME_CALL = re.compile(r'\b([A-Za-z_]\w*)\s*\(')

KEYWORDS = {'if', 'while', 'for', 'switch', 'return', 'sizeof', 'do', 'else',
            'case', 'break', 'continue', 'goto', 'defined', 'typedef'}

SKIP_FILE_PREFIX = ('stm32f10x_', 'core_cm', 'system_stm32', 'misc')


def norm(sig):
    s = sig.replace('（', '(').replace('）', ')').replace('，', ',')
    s = WS.sub(' ', s).strip()
    # `T *f(...)` 和 `T * f(...)` 是同一种写法，把星号两侧空白统一去掉再比
    s = re.sub(r'\s*(\*+)\s*', r'\1', s)
    return s.rstrip(';{').strip()


def split_args(text):
    """text 从 '(' 开始，返回 (参数串, 剩余)  —— 按括号配对取到对应的 ')'"""
    depth = 0
    for i, ch in enumerate(text):
        if ch == '(':
            depth += 1
        elif ch == ')':
            depth -= 1
            if depth == 0:
                return text[1:i], text[i + 1:]
    return None, ''


def scan_source_file(path):
    """逐行识别函数声明/定义，返回 [(函数名, 归一化签名, 位置)]"""
    try:
        src = open(path, 'r', encoding='utf-8', errors='replace').read()
    except OSError:
        return []

    lines = src.splitlines()
    found = []
    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s or s.startswith(('//', '/*', '*', '#')):
            continue

        # 本行是声明/定义的判据：以 ; 结尾，或以 { 结尾，
        # 或以 ) 结尾且下一个非空行是 {（定义把花括号写在下一行）
        ends_decl = s.endswith(';') or s.endswith('{')
        if not ends_decl and s.endswith(')'):
            for j in range(i + 1, min(i + 3, len(lines))):
                nx = lines[j].strip()
                if not nx:
                    continue
                ends_decl = nx.startswith('{')
                break
        if not ends_decl:
            continue

        m = NAME_CALL.search(s)
        if not m:
            continue
        name = m.group(1)
        if name in KEYWORDS:
            continue

        ret = s[:m.start()].strip()
        # 返回类型必须非空、不含 = ( 等，否则多半是函数调用或赋值
        if not ret or '=' in ret or '(' in ret or ',' in ret:
            continue
        ret = re.sub(r'^(static|extern|inline|__weak)\s+', '', ret).strip()
        if not ret:
            continue
        # 关键：`return W25Q64_WriteData(...)` 这种调用点，
        # 函数名不是关键字，但"返回类型"位置上是 return —— 必须按返回类型挡掉
        if ret in KEYWORDS:
            continue

        # m.end() 是函数名后、左括号后的位置，所以左括号在 m.end()-1
        args, _ = split_args(s[m.end() - 1:])
        if args is None:
            continue

        sig = norm('%s %s(%s)' % (ret, name, args))
        found.append((name, sig, '%s:%d' % (os.path.basename(path), i + 1)))
    return found


def src_functions(root_dir):
    """汇总全工程的函数签名。同名冲突时 .h 里的声明优先（那是权威接口）。"""
    funcs = {}
    for dirpath, _, files in os.walk(root_dir):
        if any(x in dirpath for x in ('Objects', 'Outputs', 'Listings', 'Doc', 'RTE')):
            continue
        for fn in files:
            if not fn.endswith(('.c', '.h')):
                continue
            if fn.startswith(SKIP_FILE_PREFIX):
                continue
            is_h = fn.endswith('.h')
            for name, sig, where in scan_source_file(os.path.join(dirpath, fn)):
                if name not in funcs or (is_h and not funcs[name][2]):
                    funcs[name] = (sig, where, is_h)
    return {k: (v[0], v[1]) for k, v in funcs.items()}


# ---------------------------------------------------------------------------
def main(docx, proj):
    docs = doc_prototypes(docx)
    funcs = src_functions(proj)

    print('=' * 80)
    print('接口文档 vs 源码 对账')
    print('  文档: %s' % os.path.basename(docx))
    print('  工程: %s' % proj)
    print('=' * 80)
    print('文档中列出的接口数 = %d' % len(docs))
    print('源码中扫到的函数数 = %d' % len(funcs))

    missing, mismatch, ok = [], [], []
    for heading, proto in docs:
        m = re.search(r'\b([A-Za-z_]\w*)\s*\(', proto)
        if not m:
            missing.append((heading, proto, '解析不出函数名'))
            continue
        name = m.group(1)
        if name not in funcs:
            missing.append((heading, proto, '源码里找不到这个函数'))
            continue
        real, where = funcs[name]
        if norm(proto) != real:
            mismatch.append((heading, proto, real, where))
        else:
            ok.append((heading, name, where))

    print('\n---- 签名一致 (%d) ----' % len(ok))
    for h, n, w in ok:
        print('  OK   %-22s  %s' % (n, w))

    if mismatch:
        print('\n---- !! 签名不一致 (%d) ----' % len(mismatch))
        for h, doc, real, where in mismatch:
            print('  [%s]' % h)
            print('     文档: %s' % doc)
            print('     源码: %s   (%s)' % (real, where))

    if missing:
        print('\n---- !! 文档写了但源码没有 (%d) ----' % len(missing))
        for h, doc, why in missing:
            print('  [%s] %s   <- %s' % (h, doc, why))

    print('\n汇总: 一致 %d / 签名不符 %d / 找不到 %d'
          % (len(ok), len(mismatch), len(missing)))
    return 1 if (mismatch or missing) else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1], sys.argv[2]))

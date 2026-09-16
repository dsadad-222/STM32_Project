# -*- coding: utf-8 -*-
"""AC5(ARMCC V5) 兼容性 lint：
   1) 字符串字面量里不能出现非 ASCII 字符（会报 #870-D invalid multibyte character sequence）
   2) 顺带提示 全局/静态 变量声明与定义类型不一致的风险（人工复核用）

中文只能写在注释里。
"""
import io, re, sys
from pathlib import Path

CJK = re.compile(r"[\u3000-\u303f\u4e00-\u9fff\uff00-\uffef\u2010-\u203b\u2500-\u257f]")


def strip_comments(text):
    """去掉注释，保留换行以维持行号"""
    out = []
    i = 0
    n = len(text)
    while i < n:
        if text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("\n" * text.count("\n", i, j))
            i = j
        elif text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        else:
            # 字符串字面量：原样保留（我们要检查的就是它）
            if text[i] == '"':
                j = i + 1
                while j < n:
                    if text[j] == "\\":
                        j += 2
                        continue
                    if text[j] == '"':
                        j += 1
                        break
                    j += 1
                out.append(text[i:j])
                i = j
            else:
                out.append(text[i])
                i += 1
    return "".join(out)


def check_file(path):
    raw = io.open(path, encoding="utf-8", errors="replace").read()
    code = strip_comments(raw)
    hits = []
    for no, line in enumerate(code.splitlines(), 1):
        if CJK.search(line):
            # 只挑双引号之间的部分
            for m in re.finditer(r'"((?:[^"\\]|\\.)*)"', line):
                if CJK.search(m.group(1)):
                    hits.append((no, m.group(1)[:60]))
    return hits


def main(roots):
    total = 0
    for root in roots:
        for p in sorted(Path(root).rglob("*")):
            if p.suffix.lower() not in (".c", ".h"):
                continue
            # 第三方库不查
            if any(k in p.parts for k in ("STM32_Library", "Arm_Kernel", "Startup")):
                continue
            hits = check_file(p)
            if hits:
                total += len(hits)
                print(f"[命中] {p}")
                for no, frag in hits:
                    print(f"      第 {no} 行字符串: {frag!r}")
    print()
    print("字符串字面量里的非 ASCII 字符:", total, "处")
    print("结果:", "OK 可以编译" if total == 0 else "需要修掉上面的地方")


if __name__ == "__main__":
    main(sys.argv[1:] or [r"D:\STM32_Project\SerialAdv_Full"])

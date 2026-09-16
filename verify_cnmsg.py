# -*- coding: utf-8 -*-
r"""核对 cn_msg.h 里所有 \xHH 中文宏按 GBK 解码是否正确（防手写字节错）。"""
import io

BS = chr(92)
path = r"D:\STM32_Project\AdcTemp_Full\App_User\cn_msg.h"
with io.open(path, "r", encoding="utf-8") as f:
    src = f.read()


def decode_c_literal(body):
    """把 C 字面量内部文本解成字节，再按 GBK 解码"""
    raw = bytearray()
    i = 0
    while i < len(body):
        if body[i] == BS and i + 1 < len(body) and body[i + 1] in "xX":
            raw.append(int(body[i + 2:i + 4], 16))
            i += 4
        elif body[i] == BS and i + 1 < len(body):
            raw.append({"r": 13, "n": 10, "t": 9}.get(body[i + 1], ord(body[i + 1])))
            i += 2
        else:
            raw.append(ord(body[i]))
            i += 1
    return bytes(raw)


bad = 0
rows = []
for line in src.splitlines():
    s = line.strip()
    if not s.startswith("#define "):
        continue
    rest = s[len("#define "):]
    parts = rest.split(None, 1)
    if len(parts) != 2:
        continue
    name, val = parts[0], parts[1].strip()
    if not val.startswith('"'):
        continue
    # 取出第一段引号内容（宏都是一段，无需处理续行拼接）
    end = val.find('"', 1)
    body = val[1:end]
    raw = decode_c_literal(body)
    try:
        text = raw.decode("gbk")
        flag = "OK "
    except UnicodeDecodeError:
        text = raw.decode("gbk", "replace")
        flag = "ERR"
        bad += 1
    rows.append((flag, name, len(raw), text))

print("=" * 74)
print("cn_msg.h 中文宏（GBK 解码回读）")
print("=" * 74)
for flag, name, n, text in rows:
    print("[%s] %-14s %3dB  %s" % (flag, name, n, text))
print()
print("共 %d 条，异常 %d 条" % (len(rows), bad))

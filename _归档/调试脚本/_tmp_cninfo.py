# -*- coding: utf-8 -*-
"""临时脚本：以 GBK 读源码，导出中文宏与关键函数语义，供逐行注释参考。"""
import io
import re

D = (r"C:\Users\y7000\Desktop\嵌入式\0916_ADC内部温度采集"
     r"\202417010304智能3班陈相林实现ADC内部温度采集"
     r"\STM32_Project\AdcTemp_Full")


def rd(p):
    return io.open(p, encoding="gbk", errors="replace").read()


def gbk_unescape(raw):
    """把 "\\xCF\\xB5" 这种转义串还原成真正的中文。"""
    try:
        bs = raw.encode("latin1").decode("unicode_escape").encode("latin1")
        return bs.decode("gbk")
    except Exception:
        return "<decode fail>"


print("=" * 60)
print("cn_msg.h 中文宏")
print("=" * 60)
t = rd(D + r"\App_User\cn_msg.h")
pat = re.compile(r'#define\s+(CN_\w+)\s+"([^"]*)"')
for m in pat.finditer(t):
    print("%-16s = %s" % (m.group(1), gbk_unescape(m.group(2))))

print()
print("=" * 60)
print("被调函数签名（从 .h 取权威声明）")
print("=" * 60)
import glob
for h in glob.glob(D + r"\Drv_Common\*.h"):
    txt = rd(h)
    for line in txt.splitlines():
        if re.match(r"^[a-zA-Z_].*\(", line) and ";" in line:
            print("%-28s | %s" % (h.split("\\")[-1], line.strip()))

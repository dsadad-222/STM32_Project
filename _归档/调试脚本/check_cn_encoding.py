# -*- coding: utf-8 -*-
"""看一看中文在 GBK / UTF-8 下各是什么字节，方便固件里直接写 \\xHH 转义"""

samples = ["温度", "温度偏高", "标定完成", "开机自检", "ADC 温度"]

for s in samples:
    gbk = s.encode("gbk")
    utf = s.encode("utf-8")
    print("文本      : %s" % s)
    print("  GBK     : %s   (%d 字节)" % (" ".join("\\x%02X" % b for b in gbk), len(gbk)))
    print("  UTF-8   : %s   (%d 字节)" % (" ".join("\\x%02X" % b for b in utf), len(utf)))
    print()

print("串口助手常见默认编码 = GBK/ANSI，所以固件按 GBK 发最省事。")
print("OLED 要显示汉字则是另一回事：需要 16x16 点阵字模，每个汉字 32 字节。")

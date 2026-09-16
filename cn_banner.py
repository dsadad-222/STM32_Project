# -*- coding: utf-8 -*-
r"""把 main.c 的开机横幅（帮助信息）换成中文版。

要点：中文按 GBK 编码写成 \xHH 转义，ASCII 原样保留；
若某个 \xHH 后面紧跟十六进制字符，必须用 " " 断开，
否则编译器会把后续字符一起吞进转义序列。
"""
import io

BS = chr(92)          # 反斜杠，避免被各种层面转义


def c_lit(s):
    out = ['"']
    prev_wide = False
    for ch in s:
        b = ch.encode("gbk")
        if len(b) == 1 and 0x20 <= b[0] < 0x7F and ch not in '"' + BS:
            if prev_wide and ch in "0123456789abcdefABCDEF":
                out.append('" "')            # 断开，防止吞字符
            out.append(ch)
            prev_wide = False
        else:
            for x in b:
                out.append(BS + "x%02X" % x)
            prev_wide = True
    out.append('"')
    return "".join(out)


LINES = [
    "中文 : 本工程 = 串口控制 + ADC 内部温度采集（chapter8）",
    "ADC  : ADC1 通道16 内部温度传感器，每 2 秒采集一次",
    "温度 : 读的是芯片自身温度（结温），不是室温",
    "OLED : 0.86 寸 128x32，软件 I2C1  PB6=SCL  PB7=SDA",
    "存储 : 内部 Flash 最后一页 0x0807F800",
    "控制 : 55 FF 03 06 <00左转 01右转 02蜂鸣器 03灯条> <00关 01开>",
    "文本 : 55 FF <len> 07 <text>   len = 1 + 字符个数",
    "存储 : 55 FF 02 08 <00保存 01清除 02读回>",
    "快捷 : L/R/B/D <1或0> 开/关   T<文本>   S保存  C清除  P读回   A立即采样",
    "标定 : K<室温> 回车 = 标定     Z = 清除标定",
    "按键 : KEY1 切换页面   KEY2 呼吸灯(左转灯)   KEY3 立即采样",
]

OLD_LINES = [
    'ADC  : ADC1 channel16 internal temp sensor, every 2s',
    "TEMP : reads the chip's own die temperature, NOT ambient air",
    'OLED : 0.86 inch, I2C1 PB6=SCL PB7=SDA',
    'FLASH: internal, page 0x0807F800',
    'ctrl : 55 FF 03 06 <00 left|01 right|02 beep|03 led> <00 off|01 on>',
    'text : 55 FF <len> 07 <text>       (len = 1 + char count)',
    'store: 55 FF 02 08 <00 save|01 clear|02 reload>',
    'fast : L/R/B/D <1|0>   T <text>   S/C/P   A=sample now',
    'cal  : K <ref C> <enter> = calibrate   Z = clear calibration',
    'key  : KEY1 page  KEY2 breath(LEFT lamp)  KEY3 sample now',
]

NL = BS + "r" + BS + "n"
old = "".join('    Usart_SendString("%s%s");\n' % (t, NL) for t in OLD_LINES)
new = "".join('    Usart_SendString(%s "%s");\n' % (c_lit(t), NL) for t in LINES)

path = r"D:\STM32_Project\AdcTemp_Full\App_User\main.c"
with io.open(path, "r", encoding="utf-8") as f:
    src = f.read()

if old not in src:
    print("!! 未匹配到原横幅（可能已替换过）")
else:
    src = src.replace(old, new)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    print("OK：横幅已替换为中文，共 %d 行" % len(LINES))

for t, l in zip(LINES, new.splitlines()):
    print(t)
    print("    ->", l[:120])

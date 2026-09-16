# -*- coding: utf-8 -*-
import io

def c_lit(s):
    """把字符串转成 C 字面量：中文转 GBK \xHH，ASCII 原样；遇到 \xHH 后紧跟
       十六进制字符时用 " " 断开，避免编译器把后续字符吞进转义里。"""
    out = ['"']
    prev_wide = False
    for ch in s:
        b = ch.encode("gbk")
        if len(b) == 1 and 0x20 <= b[0] < 0x7F and ch not in '"\':
            if prev_wide and ch in "0123456789abcdefABCDEF":
                out.append('" "')
            out.append(ch)
            prev_wide = False
        else:
            for x in b:
                out.append("\x%02X" % x)
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

old = (
'    Usart_SendString("ADC  : ADC1 channel16 internal temp sensor, every 2s\r\n");\n'
'    Usart_SendString("TEMP : reads the chip\'s own die temperature, NOT ambient air\r\n");\n'
'    Usart_SendString("OLED : 0.86 inch, I2C1 PB6=SCL PB7=SDA\r\n");\n'
'    Usart_SendString("FLASH: internal, page 0x0807F800\r\n");\n'
'    Usart_SendString("ctrl : 55 FF 03 06 <00 left|01 right|02 beep|03 led> <00 off|01 on>\r\n");\n'
'    Usart_SendString("text : 55 FF <len> 07 <text>       (len = 1 + char count)\r\n");\n'
'    Usart_SendString("store: 55 FF 02 08 <00 save|01 clear|02 reload>\r\n");\n'
'    Usart_SendString("fast : L/R/B/D <1|0>   T <text>   S/C/P   A=sample now\r\n");\n'
'    Usart_SendString("cal  : K <ref C> <enter> = calibrate   Z = clear calibration\r\n");\n'
'    Usart_SendString("key  : KEY1 page  KEY2 breath(LEFT lamp)  KEY3 sample now\r\n");\n'
)

new = "".join('    Usart_SendString(%s "\r\n");\n' % c_lit(t) for t in LINES)

path = r"D:\STM32_Project\AdcTemp_Full\App_User\main.c"
with io.open(path, "r", encoding="utf-8") as f:
    src = f.read()

if old not in src:
    print("!! 未匹配到原横幅，检查是否已替换过")
else:
    src = src.replace(old, new)
    with io.open(path, "w", encoding="utf-8", newline="") as f:
        f.write(src)
    print("横幅已替换为中文，共 %d 行" % len(LINES))

# 打印结果供核对
for l in new.splitlines():
    print(l[:110])

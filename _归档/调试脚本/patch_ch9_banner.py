# -*- coding: utf-8 -*-
"""重写 main.c 的开机串口横幅（中文转 GBK \\xNN 转义，避免 AC5 #870-D 警告）"""
import io

P = r"D:\STM32_Project\FlashRW_Full\App_User\main.c"

s = io.open(P, encoding="utf-8", errors="surrogateescape").read()

START = '    Usart_SendString("\\r\\n=== AdcTemp Full'
i0 = s.find(START)
if i0 < 0:
    raise SystemExit("!! 找不到横幅起始")
i1 = s.find('/* 中文提示（GBK 编码）*/', i0)
if i1 < 0:
    raise SystemExit("!! 找不到横幅结尾")
i1 = s.find("\n", i1) + 1

LINES = [
    "=== FlashRW Full (chapter9)   115200-8-N-1 ===",
    "中文: 本工程 = 内部FLASH + 外部W25Q64 读写（chapter9）",
    "温度: ADC1 通道16 片内温度传感器，每 2 秒采集一次；串口只报温度",
    "OLED: 0.86 寸 128x32，软件 I2C1  PB6=SCL  PB7=SDA",
    "      第1行=内部FLASH数据  第2行=温度Temp  第3行=外部FLASH数据  第4行=状态",
    "FLASH: 内部 0x0807F000(数据页) / 0x0807F800(状态页)",
    "       外部 W25Q64 8MB @SPI2  PB12=CS PB13=SCK PB14=MISO PB15=MOSI",
    "存储: 55 FF <len> 07 <01内部 02外部> <数据> <异或>    len = 1+1+N，N最大20",
    "      例: 55 FF 07 07 01 01 02 03 04 05 <异或>  -> 01 02 03 04 05 存内部",
    "控制: 55 FF 03 06 <00左转 01右转 02蜂鸣器 03灯条> <00关 01开>",
    "文本: 55 FF <len> 09 <文本>    len = 1 + 字符数",
    "状态: 55 FF 02 08 <00保存 01清除 02读回>",
    "快捷: L/R/B/D <1或0> 开/关   T<文本>   S保存 C清除 P读回   A立即采样",
    "标定: K<室温> 回车 = 标定     Z = 清除标定",
    "按键: KEY1 读内部FLASH   KEY2 呼吸灯(左转灯)   KEY3 读外部FLASH",
]


def esc(text):
    out = []
    for ch in text:
        if ord(ch) < 128:
            out.append("\\" + ch if ch in '"\\' else ch)
        else:
            for b in ch.encode("gbk"):
                out.append("\\x%02X" % b)
    return "".join(out)


body = []
for ln in LINES:
    body.append('    Usart_SendString("%s\\r\\n");\n' % esc(ln))
body.append('    Usart_SendString("Info : " CN_BOOT_OK "\\r\\n");       /* 中文提示（GBK 编码）*/\n')

new_block = "".join(body)
s = s[:i0] + new_block + s[i1:]
io.open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)

print("横幅已重写: %d 行" % len(LINES))
# 自检：确认没有裸非 ASCII 出现在新的字符串字面量里
bad = [ln for ln in body if any(ord(c) > 127 for c in ln)]
print("裸非 ASCII 行数:", len(bad))

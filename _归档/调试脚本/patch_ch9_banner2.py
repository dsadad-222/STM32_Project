# -*- coding: utf-8 -*-
"""
重写 main.c 的开机串口横幅（第 2 版）。

关键坑：C 语言的 \\x 转义会**吃掉尽可能多的十六进制数字**，不是固定 2 位。
所以 "\\xBFFLASH" 会被解析成 \\xBFF（越界 -> AC5 warning #27-D）。
修法：转义后面紧跟 [0-9A-Fa-f] 时，用字符串拼接断开 —— "\\xBF" "FLASH"。
"""
import io

P = r"D:\STM32_Project\FlashRW_Full\App_User\main.c"
HEXCHARS = set("0123456789ABCDEFabcdef")

s = io.open(P, encoding="utf-8", errors="surrogateescape").read()

START = '    Usart_SendString("=== FlashRW Full'
i0 = s.find(START)
if i0 < 0:
    raise SystemExit("!! 找不到横幅起始")
i1 = s.find("CN_BOOT_OK", i0)
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
    """把一行文本转成 C 字符串字面量的内容部分（非 ASCII -> GBK \\xNN），
    必要时用 '" "' 断开，防止 \\xNN 吞掉后面的十六进制字符。"""
    # 先切成 token：ASCII 单字符 / GBK 转义
    toks = []
    for ch in text:
        if ord(ch) < 128:
            toks.append(("raw", "\\" + ch if ch in '"\\' else ch))
        else:
            for b in ch.encode("gbk"):
                toks.append(("esc", "\\x%02X" % b))

    out = []
    for idx, (kind, tok) in enumerate(toks):
        out.append(tok)
        if kind == "esc" and idx + 1 < len(toks):
            nk, ntok = toks[idx + 1]
            if nk == "raw" and ntok and ntok[0] in HEXCHARS:
                out.append('" "')          # 断开，避免转义吞字符
    return "".join(out)


body = []
for ln in LINES:
    body.append('    Usart_SendString("%s\\r\\n");\n' % esc(ln))
body.append('    Usart_SendString("Info : " CN_BOOT_OK "\\r\\n");\n')

new_block = "".join(body)
s = s[:i0] + new_block + s[i1:]
io.open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)

print("横幅已重写: %d 行" % len(LINES))
bad = [ln for ln in body if any(ord(c) > 127 for c in ln)]
print("裸非 ASCII 行数:", len(bad))
print("断开处数量:", sum(1 for ln in body if '" "' in ln))

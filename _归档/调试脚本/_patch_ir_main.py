# -*- coding: utf-8 -*-
"""把需求5（红外避障）接进 IrAvoid_Full/App_User/main.c。

按键分配按用户决定：KEY1/2/3 全让给需求5，原功能挪到串口命令：
    O = 原 KEY1（测距并存外部 FLASH）      E = 原 KEY3（读外部 FLASH 文本）
    Q / J / V = 左 / 右 / 左右都测          # = 打印 GPIOA、GPIOF 输入寄存器

写法要点：中文串一律整行转成 GBK 转义，不做 C 相邻字符串拼接
（混着写很容易把引号配错，上一版就是这么挂的）。
"""
import io
import os

P = r"D:\STM32_Project\IrAvoid_Full\App_User\main.c"

raw = io.open(P, "rb").read()
n_crlf = raw.count(b"\r\n")
n_lf = raw.count(b"\n") - n_crlf
use_crlf = n_crlf > n_lf
src = raw.decode("utf-8").replace("\r\n", "\n")
print("原文件换行：%s（CRLF %d / 裸LF %d）" % ("CRLF" if use_crlf else "LF", n_crlf, n_lf))

n = [0]


def cstr(s):
    """Python 字符串 -> C 源码字面量。
    ASCII 可见字符原样保留（日志/源码都好看），其余按 GBK 转成 \\xXX ——
    串口那一端一直按 GBK 解码中文，所以中文必须发 GBK 字节，不能发 UTF-8。"""
    out = []
    for ch in s:
        o = ord(ch)
        if 0x20 <= o <= 0x7E and ch not in '"\\?':
            out.append(ch)
        else:
            out.extend("\\x%02X" % b for b in ch.encode("gbk"))
    return '"' + "".join(out) + '"'


def rep(old, new, label):
    global src
    c = src.count(old)
    assert c == 1, "[%s] 锚点命中 %d 次（应为 1）" % (label, c)
    src = src.replace(old, new, 1)
    n[0] += 1
    print("  [%2d] %s" % (n[0], label))


def insert_after(needle, extra, label):
    global src
    lines = src.split("\n")
    idx = [i for i, l in enumerate(lines) if needle in l]
    assert len(idx) == 1, "[%s] 命中 %d 行" % (label, len(idx))
    lines[idx[0] + 1:idx[0] + 1] = extra
    src = "\n".join(lines)
    n[0] += 1
    print("  [%2d] %s" % (n[0], label))


# ---------------------------------------------------------------- 1. include
rep('#include "hcsr04_drv.h"\n#include "cn_msg.h"',
    '#include "hcsr04_drv.h"\n#include "ir_drv.h"\n#include "cn_msg.h"',
    "include ir_drv.h")

# ---------------------------------------------------------------- 2. 全局状态
rep('static uint8_t      s_line3Mode    = 0;         /* OLED 第 3 行：0=外部文本记录(需求3)，1=距离记录(需求4) */',
    '''static uint8_t      s_line3Mode    = 0;         /* OLED 第 3 行：0=外部文本(需求3)，1=距离(需求4)，2=红外避障(需求5) */

/* ---- 需求5：红外避障对管（板载两路，反相输出：有障碍 = 高电平）---- */
static uint8_t      s_irLeft       = 0;         /* 左路最近一次读数：1 = 有障碍 */
static uint8_t      s_irRight      = 0;         /* 右路最近一次读数：1 = 有障碍 */
static uint8_t      s_irLeftValid  = 0;         /* 1 = 这一路已经测过（没测过屏上显示 '-'）*/
static uint8_t      s_irRightValid = 0;''',
    "s_line3Mode 注释 + 红外状态变量")

# ---------------------------------------------------------------- 3. 前置声明
rep('static void Key2ReadNext(void);',
    '''static void Key1MeasureAndStore(void);
static void Key2ReadNext(void);
static void Key3ReadExternal(void);
static void KeyIrLeft(void);
static void KeyIrRight(void);
static void KeyIrBoth(void);
static void DumpIrPins(void);''',
    "前置声明")

# ---------------------------------------------------------------- 4. BuildIrLine
rep('/* 第 3 行（需求4 模式）：距离记录。',
    '''/* 第 3 行（需求5 模式）：红外避障读数。
 * 一行 16 字符，格式：  IR L:1 R:0
 *     1 = 检测到障碍（对管输出为高）  0 = 无障碍  '-' = 这一路还没测过 */
static void BuildIrLine(char *line)
{
    uint8_t pos = 0;

    AppendTextX(line, &pos, "IR L:");
    line[pos++] = (s_irLeftValid != 0) ? (char)('0' + s_irLeft) : '-';

    AppendTextX(line, &pos, " R:");
    line[pos++] = (s_irRightValid != 0) ? (char)('0' + s_irRight) : '-';

    PadLine(line, &pos);
}

/* 第 3 行（需求4 模式）：距离记录。''',
    "新增 BuildIrLine")

# ---------------------------------------------------------------- 5. UpdateDisplay
rep('''    /* 第 3 行：外部 FLASH 数据（需求3）/ 距离记录（需求4），谁操作就显示谁 */
    if (s_line3Mode != 0u)
    {
        BuildDistLine(line);
    }
    else
    {
        BuildFlashLine(line, "EX:", s_exData, s_exLen, s_exValid);
    }''',
    '''    /* 第 3 行：外部 FLASH 数据(需求3) / 距离记录(需求4) / 红外避障(需求5)，谁操作就显示谁 */
    if (s_line3Mode == 2u)
    {
        BuildIrLine(line);
    }
    else if (s_line3Mode != 0u)
    {
        BuildDistLine(line);
    }
    else
    {
        BuildFlashLine(line, "EX:", s_exData, s_exLen, s_exValid);
    }''',
    "UpdateDisplay 三分支")

# ---------------------------------------------------------------- 6. 命令表注释 + 新命令
rep('''             * M / N / X / W : 测距 / 读下一条距离记录 / 清空距离区 / 呼吸灯开关
             * I             : 读内部 FLASH 数据（原 KEY1 的功能）
             */''',
    '''             * M / N / X / W : 测距 / 读下一条距离记录 / 清空距离区 / 呼吸灯开关
             * I             : 读内部 FLASH 数据
             * O / E         : 测距并存入外部 FLASH / 读外部 FLASH 文本（原 KEY1、KEY3 移过来）
             * Q / J / V     : 需求5 —— 测左侧 / 测右侧 / 左右都测并打印
             * #             : 打印 GPIOA、GPIOF 输入寄存器（用来定位对管接在哪两个脚）
             */''',
    "命令表注释")

rep('''                    Usart_SendString("IN   : internal flash empty\\r\\n");
                }
                UpdateDisplay();
            }
            break;''',
    '''                    Usart_SendString("IN   : internal flash empty\\r\\n");
                }
                UpdateDisplay();
            }
            else if (byte == 'O')
            {
                /* 需求5 把 KEY1 让给了红外避障，原来"测距并存入外部 FLASH"的
                   功能挪到这个命令上，保证需求4 的验收项一个不少。*/
                Key1MeasureAndStore();
            }
            else if (byte == 'E')
            {
                /* 同理：原 KEY3（读外部 FLASH 文本记录）挪到 'E' */
                Key3ReadExternal();
            }
            else if (byte == 'Q')
            {
                KeyIrLeft();                    /* 需求5-1：测左侧 */
            }
            else if (byte == 'J')
            {
                KeyIrRight();                   /* 需求5-1：测右侧 */
            }
            else if (byte == 'V')
            {
                KeyIrBoth();                    /* 需求5-2：左右都测并打串口 */
            }
            else if (byte == '#')
            {
                DumpIrPins();                   /* 调试：打印两个端口的输入电平 */
            }
            break;''',
    "新增 O/E/Q/J/V/# 命令")

# ---------------------------------------------------------------- 7. 红外函数 + HandleKey
rep('''static void HandleKey(KeyEvent ev)
{
    switch (ev)
    {
        case KEY_EVT_KEY1_CLICK:        /* 需求4-1：测距 -> 存外部 FLASH */
            Key1MeasureAndStore();
            break;

        case KEY_EVT_KEY2_CLICK:        /* 需求4-2：顺序读一条 -> 显示 + 联动 */
            Key2ReadNext();
            break;

        case KEY_EVT_KEY3_CLICK:        /* 需求3：读外部 FLASH 文本记录 */
            Key3ReadExternal();
            break;

        default:
            break;
    }
}''',
    '''/* ========================= 需求5：红外避障 ========================= */

/* 打印一个 16 位值的十六进制（DumpIrPins 用） */
static void DumpHex16(uint16_t v)
{
    static const char hex[] = "0123456789ABCDEF";
    char buf[5];

    buf[0] = hex[(v >> 12) & 0x0Fu];
    buf[1] = hex[(v >> 8) & 0x0Fu];
    buf[2] = hex[(v >> 4) & 0x0Fu];
    buf[3] = hex[v & 0x0Fu];
    buf[4] = '\\0';
    Usart_SendString(buf);
}

/* 把一路读数报到串口：原始电平 + 判定结果。
 * 原始电平一并打出来，上板核对引脚时能直接看到"盖住对管前后哪一位翻了"。*/
static void ReportIr(const char *tag, uint8_t isLeft)
{
    Usart_SendString("IR   : ");
    Usart_SendString(tag);
    Usart_SendString(" raw=");
    Usart_SendString((Ir_ReadRaw(isLeft) != 0u) ? "1" : "0");
    Usart_SendString("  -> ");
    Usart_SendString((Ir_IsBlocked(isLeft) != 0u) ? "BLOCKED" : "CLEAR");
    Usart_SendString("\\r\\n");
}

/* 需求5-1：KEY1 单击 —— 完成左侧红外的测量并显示 */
static void KeyIrLeft(void)
{
    s_irLeft      = Ir_IsBlocked(1u);
    s_irLeftValid = 1u;
    s_line3Mode   = 2u;                 /* 第 3 行切到红外版式 */
    SetMessage("IR LEFT DONE");
    ReportIr("left ", 1u);
    UpdateDisplay();
}

/* 需求5-1：KEY2 单击 —— 完成右侧红外的测量并显示 */
static void KeyIrRight(void)
{
    s_irRight      = Ir_IsBlocked(0u);
    s_irRightValid = 1u;
    s_line3Mode    = 2u;
    SetMessage("IR RIGHT DONE");
    ReportIr("right", 0u);
    UpdateDisplay();
}

/* 需求5-2：KEY3 单击 —— 左右两路一起测，结果通过串口打印到 PC */
static void KeyIrBoth(void)
{
    s_irLeft       = Ir_IsBlocked(1u);
    s_irRight      = Ir_IsBlocked(0u);
    s_irLeftValid  = 1u;
    s_irRightValid = 1u;
    s_line3Mode    = 2u;
    SetMessage("IR BOTH DONE");

    Usart_SendString("IR   : both sensors measured\\r\\n");
    ReportIr("left ", 1u);
    ReportIr("right", 0u);
    Usart_SendString("IR   : L=");
    Usart_SendString((s_irLeft != 0u) ? "1" : "0");
    Usart_SendString(" R=");
    Usart_SendString((s_irRight != 0u) ? "1" : "0");
    Usart_SendString("   (1=blocked 0=clear)\\r\\n");

    UpdateDisplay();
}

/* 调试辅助：把 GPIOA / GPIOF 的输入数据寄存器整个打出来。
 * 用途：确认两路对管究竟接在哪两个引脚上 —— 把对管遮住/移开，各敲一次 #，
 * 对比哪一位翻转，那一位就是这一路。
 * （批量扫描用的是 D:\\STM32_Project\\_ir_block_test.py）*/
static void DumpIrPins(void)
{
    SetMessage("IR PIN SCAN");
    UpdateDisplay();

    Usart_SendString("IR   : GPIOA_IDR=0x");
    DumpHex16(GPIO_ReadInputData(GPIOA));
    Usart_SendString("  GPIOF_IDR=0x");
    DumpHex16(GPIO_ReadInputData(GPIOF));
    Usart_SendString("\\r\\n");
}

static void HandleKey(KeyEvent ev)
{
    switch (ev)
    {
        case KEY_EVT_KEY1_CLICK:        /* 需求5-1：测左侧红外避障 */
            KeyIrLeft();
            break;

        case KEY_EVT_KEY2_CLICK:        /* 需求5-1：测右侧红外避障 */
            KeyIrRight();
            break;

        case KEY_EVT_KEY3_CLICK:        /* 需求5-2：左右都测并通过串口打印 */
            KeyIrBoth();
            break;

        default:
            break;
    }
}''',
    "红外函数 + 新 HandleKey")

# ---------------------------------------------------------------- 8. 初始化
rep('    Hcsr04_Init();                  /* 超声波 HC-SR04：TRIG=PF11 ECHO=PF12，计时用 TIM4 */',
    '''    Hcsr04_Init();                  /* 超声波 HC-SR04：TRIG=PF11 ECHO=PF12，计时用 TIM4 */
    Ir_Init();                      /* 需求5：红外避障对管（PA0 = 左，PA1 = 右）*/''',
    "Ir_Init 初始化")

# ---------------------------------------------------------------- 9. 启动横幅
lines = src.split("\n")
banner = [i for i, l in enumerate(lines) if "=== RadarFlash Full" in l]
assert len(banner) == 1, "横幅行命中 %d" % len(banner)
lines[banner[0]] = ("    Usart_SendString("
                    + cstr("=== IrAvoid Full (红外避障 + 超声波测距 + FLASH 存储)   "
                           "115200-8-N-1 ===\r\n") + ");")
src = "\n".join(lines)
n[0] += 1
print("  [%2d] 启动横幅" % n[0])

# 在"第1行=... 第4行=状态"那行之后插入两行红外说明
# （锚点用那行独有的尾巴 "4行=状态"，避免 "Temp" 这种满屏都有的词）
insert_after('"4\\xD0\\xD0=\\xD7\\xB4\\xCC\\xAC', [
    "    Usart_SendString(" + cstr("IR  : 板载两路红外避障对管，反相输出（有障碍=高电平）  "
                                 "PA0=左  PA1=右\r\n") + ");",
    "    Usart_SendString(" + cstr("KEY : KEY1=测左  KEY2=测右  KEY3=左右都测并打印"
                                 "（原 KEY1 测距存储改敲 O，原 KEY3 读外部 FLASH 改敲 E）\r\n") + ");",
], "横幅说明补充")

# ---------------------------------------------------------------- 10. 文件头注释
rep('  *          【本次实训（任务实训10 · 需求4）新增 —— 超声波测距 + 片外 FLASH 存储 + 距离联动】',
    '''  *          【本次实训（任务实训11 · 需求5）新增 —— 左右红外避障传感器采集】
 *          1. KEY1(PG3) 单击：测左侧红外避障，结果显示到 OLED 第 3 行并打串口。
 *          2. KEY2(PG4) 单击：测右侧红外避障，同上。
 *          3. KEY3(PG5) 单击：左右两路一起测，结果通过串口打印到 PC。
 *          4. 板上两路对管（D7/D8 + R17/R18 + Q1/Q2 SS8550）是【反相输出】：
 *             前方有障碍、反射强时引脚为高电平，空旷时为低。判"有障碍"要看高，
 *             写代码最容易在这里搞反。
 *          5. 因为 KEY1/KEY2/KEY3 已全被本需求占用，需求4 的原 KEY1（测距并存入
 *             外部 FLASH）改到串口命令 'O'，需求3 的原 KEY3（读外部 FLASH 文本）
 *             改到 'E'，功能一个不少；串口另加 Q/J/V 做同样的红外测量。
 *          6. PIN：红外左 = PA0，红外右 = PA1。
 *
 *          【本次实训（任务实训10 · 需求4）新增 —— 超声波测距 + 片外 FLASH 存储 + 距离联动】''',
    "文件头注释")

# ---------------------------------------------------------------- 写回
out = src if not use_crlf else src.replace("\n", "\r\n")
io.open(P, "wb").write(out.encode("utf-8"))
print("\n共改动 %d 处，写入 %d 字节" % (n[0], os.path.getsize(P)))

back = io.open(P, encoding="utf-8").read()
for key in ("ir_drv.h", "BuildIrLine", "KeyIrLeft", "KeyIrRight", "KeyIrBoth",
            "DumpIrPins", "Ir_Init();", "GPIOA_IDR=0x", "IrAvoid Full"):
    assert key in back, "回读缺少 %s" % key
print("回读校验：关键内容全部就位")

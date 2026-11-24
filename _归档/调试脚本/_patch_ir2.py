# -*- coding: utf-8 -*-
"""
_patch_ir2.py —— 把需求5（红外避障）按【原理图确认后的正确引脚】接进 main.c

背景：第一版驱动的引脚是猜的（PA0/PA1），逻辑方向也写反了（当成"有障碍=高"）。
      查原理图 YB-DSF01-V1.0 第 2 页 + U1B 页后确定：
          P1 = PE5  左发射管驱动（开漏，低 = 亮）
          P3 = PE6  右发射管驱动
          P2 = PF9  左接收管输出（3V3 上拉，有障碍 = 低，ADC3_IN7）
          P4 = PF10 右接收管输出（ADC3_IN8）
      于是本脚本把 main.c 里所有涉及引脚 / 逻辑方向 / 显示格式的地方一次改到位。

编码：main.c 是 UTF-8 + CRLF。全程以 newline='' 读写，保留原有行尾，
      所有锚点用 A() 把 \n 展开成 \r\n 再匹配。
"""

import io, os, sys

MAIN_C = r"D:\STM32_Project\IrAvoid_Full\App_User\main.c"


def A(s):
    """把 \n 展开成 \r\n（main.c 是 CRLF）"""
    return s.replace("\n", "\r\n")


HEXD = "0123456789abcdefABCDEF"


def cstr(s):
    """把一段要发给 PC 的文本变成 C 字符串字面量：
       ASCII 可见字符原样保留，其余按 GBK 转成 \\xXX 转义（串口端按 GBK 解码）。

       ★ 必须处理的坑：C 的 \\x 转义会【尽可能多】地吃十六进制字符。
         所以 \\xAD 后面如果紧跟 '1'（如 "\\xBE\\xAD10K"），编译器读成 \\xAD1，
         直接报 #27-D: character value is out of range。
         出现在 \\xXX 之后且属于 [0-9A-Fa-f] 的字符，必须把字符串断开
         （写成相邻字面量 "..." "..."）把它隔开。"""
    parts = []
    for ch in s:
        o = ord(ch)
        if 0x20 <= o <= 0x7E and ch not in '"\\?':
            parts.append(("c", ch))
        else:
            for b in ch.encode("gbk"):
                parts.append(("x", "\\x%02X" % b))

    out = []
    prev_is_x = False
    for kind, val in parts:
        if prev_is_x and kind == "c" and val in HEXD:
            out.append('" "')               # 断开：闭合当前字面量 + 重新开一个
        out.append(val)
        prev_is_x = (kind == "x")
    return '"' + "".join(out) + '"'


raw = io.open(MAIN_C, "r", encoding="utf-8", newline="").read()
lines = raw.split("\r\n")
orig = raw

hits = []


def rep(old, new, tag):
    """整段精确替换，必须恰好命中一次"""
    global raw
    n = raw.count(old)
    if n != 1:
        print("!! [%s] 命中 %d 次（要求 1 次）" % (tag, n))
        sys.exit(1)
    raw = raw.replace(old, new)
    hits.append(tag)


def rep_line(needles, new_line, tag):
    """替换【含有全部 needles】的那一整行，必须唯一"""
    global raw
    ls = raw.split("\r\n")
    idx = [i for i, l in enumerate(ls) if all(k in l for k in needles)]
    if len(idx) != 1:
        print("!! [%s] 匹配到 %d 行（要求 1 行）" % (tag, len(idx)))
        for i in idx:
            print("     line %d: %s" % (i + 1, ls[i][:110]))
        sys.exit(1)
    ls[idx[0]] = new_line
    raw = "\r\n".join(ls)
    hits.append(tag)


# ============================================================
# P1. 文件头第 4 条：把"反相输出（有障碍=高）"改成正确描述
# ============================================================
rep(A(""" *          4. 板上两路对管（D7/D8 + R17/R18 + Q1/Q2 SS8550）是【反相输出】：
 *             前方有障碍、反射强时引脚为高电平，空旷时为低。判"有障碍"要看高，
 *             写代码最容易在这里搞反。
"""),
    A(""" *          4. 板上两路对管是【发射管 + 接收管】两组分立元件，不是三线一体模块：
 *             发射管必须 MCU 自己驱动 —— 基极回路接在 5V 上（PNP SS8550），
 *             所以驱动脚配【开漏输出】：写低 = 基极被拉低 = 发射管亮，
 *             写高 = 引脚高阻 = 发射管灭（推挽写高是关不断的，Vbe 还有 1.7V）。
 *             接收管集电极被 10K 上拉到 3V3，见光才导通，于是
 *                 ★ 有障碍（有反射）= 低电平，前方空旷 = 高电平 —— 最容易写反。
 *             测量不用单纯的高低电平，而是接 ADC3 做"灭灯/亮灯差分"，
 *             既能分远/中/近三档，又自动扣掉环境光的影响。
"""), "P1 文件头 第4条")

# ============================================================
# P2. 文件头第 6 条：引脚
# ============================================================
rep(A(" *          6. PIN：红外左 = PA0，红外右 = PA1。\n"),
    A(""" *          6. PIN（依据原理图 YB-DSF01-V1.0 第 2 页 / U1B 页）：
 *                 左发射管 P1 = PE5    右发射管 P3 = PE6   （开漏，低 = 亮）
 *                 左接收管 P2 = PF9    右接收管 P4 = PF10  （ADC3_IN7 / IN8，
 *                                                       3V3 上拉，有障碍 = 低）
"""), "P2 文件头 引脚")

# ============================================================
# P3. 前置声明区：加 AppendDigits4
# ============================================================
rep(A("""static void KeyIrLeft(void);
static void KeyIrRight(void);
static void KeyIrBoth(void);
static void DumpIrPins(void);
"""),
    A("""static void AppendDigits4(char *line, uint8_t *pos, uint16_t v);
static void KeyIrLeft(void);
static void KeyIrRight(void);
static void KeyIrBoth(void);
static void DumpIrPins(void);
"""), "P3 前置声明")

# ============================================================
# P4. 状态变量：加两路完整测量结果
# ============================================================
rep(A("""/* ---- 需求5：红外避障对管（板载两路，反相输出：有障碍 = 高电平）---- */
static uint8_t      s_irLeft       = 0;         /* 左路最近一次读数：1 = 有障碍 */
static uint8_t      s_irRight      = 0;         /* 右路最近一次读数：1 = 有障碍 */
"""),
    A("""/* ---- 需求5：红外避障对管（左发 PE5 / 右发 PE6；左收 PF9 / 右收 PF10）----
   接收管被 10K 上拉，见光导通，所以【有障碍 = 低电平】。
   这里存的是完整测量结果（本底 / 反射 / 差值 / 分档），测量过程在 ir_drv.c 里。*/
static IrResult_t   s_irL;                      /* 左路最近一次完整测量结果 */
static IrResult_t   s_irR;                      /* 右路最近一次完整测量结果 */
static uint8_t      s_irLeft       = 0;         /* 左路最近一次读数：1 = 有障碍 */
static uint8_t      s_irRight      = 0;         /* 右路最近一次读数：1 = 有障碍 */
"""), "P4 状态变量")

# ============================================================
# P5. BuildIrLine：从"高低电平 1/0"改成"距离分级单词"，并新增 BuildIrDiffLine
# ============================================================
rep(A("""/* 第 3 行（需求5 模式）：红外避障读数。
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
"""),
    A("""/* 第 3 行（需求5 模式）：红外避障距离分级。一行 16 字符，格式：
 *     IR L:NEAR R:FAR
 * 每个单词固定 4 列：NEAR（近）/ MID （中）/ FAR （远）/ ----（这一路还没测过）
 * 分级依据是"反射强度差值"，差分测量 + 门限见 ir_drv.c。 */
static void BuildIrLine(char *line)
{
    uint8_t pos = 0;

    AppendTextX(line, &pos, "IR L:");
    if (s_irLeftValid != 0)
    {
        AppendTextX(line, &pos, Ir_LevelWord(s_irL.level));
    }
    else
    {
        AppendTextX(line, &pos, "----");
    }

    AppendTextX(line, &pos, " R:");
    if (s_irRightValid != 0)
    {
        AppendTextX(line, &pos, Ir_LevelWord(s_irR.level));
    }
    else
    {
        AppendTextX(line, &pos, "----");
    }

    PadLine(line, &pos);
}

/* 第 4 行（需求5 模式）：两路反射强度原始差值。一行 16 字符，格式：
 *     dL:0120 dR:0000
 * 差值 = 灭灯读数 - 亮灯读数（ADC3 原始值），越大说明反射越强、障碍越近。
 * 现场标定门限（IR_DIFF_MID / IR_DIFF_NEAR）时就照这一行读数改。 */
static void BuildIrDiffLine(char *line)
{
    uint8_t pos = 0;

    AppendTextX(line, &pos, "dL:");
    AppendDigits4(line, &pos, (s_irLeftValid  != 0) ? s_irL.diff : 0u);
    AppendTextX(line, &pos, " dR:");
    AppendDigits4(line, &pos, (s_irRightValid != 0) ? s_irR.diff : 0u);

    PadLine(line, &pos);
}
"""), "P5 BuildIrLine")

# ============================================================
# P6. UpdateDisplay 第 4 行
# ============================================================
rep(A("""    /* 第 4 行：状态 / 提示 */
    OLED_ShowString(0, 3, s_msg);
"""),
    A("""    /* 第 4 行：红外模式下摆两路反射强度原始差值，其余情况是状态 / 提示 */
    if (s_line3Mode == 2u)
    {
        BuildIrDiffLine(line);
        OLED_ShowString(0, 3, line);
    }
    else
    {
        OLED_ShowString(0, 3, s_msg);
    }
"""), "P6 UpdateDisplay 第4行")

# ============================================================
# P7. 整块替换「需求5」实现段（从段标题到 HandleKey 之前）
# ============================================================
NEW_BLOCK = A("""/* ========================= 需求5：红外避障采集 =========================
 *
 * 板上是两组【分立对管】（发射管 + 接收管），不是三线一体模块，所以每测一次
 * 都要"先给发射管通电，再读接收管"，而且两个发射管不能同时亮（会互相照到）：
 *      左发射 P1 = PE5  开漏输出，低 = 亮      左接收 P2 = PF9  = ADC3_IN7
 *      右发射 P3 = PE6  开漏输出，低 = 亮      右接收 P4 = PF10 = ADC3_IN8
 * 接收管集电极被 10K 上拉到 3V3，见光导通 —— 有障碍 = 低电平。
 * 测量用"灭灯本底 - 亮灯读数"的差值当反射强度，既分远/中/近，又扣掉环境光。
 * 具体采集与分档在 Drv_Common/ir_drv.c，这里只负责按键 / 显示 / 串口上报。
 */

/* 往一行里追加一个 4 位定宽十进制数（不足补 0），屏上两列才对得齐 */
static void AppendDigits4(char *line, uint8_t *pos, uint16_t v)
{
    if (v > 9999u)
    {
        v = 9999u;
    }

    line[(*pos)++] = (char)('0' + ((v / 1000u) % 10u));
    line[(*pos)++] = (char)('0' + ((v / 100u) % 10u));
    line[(*pos)++] = (char)('0' + ((v / 10u) % 10u));
    line[(*pos)++] = (char)('0' + (v % 10u));
}

/* 把一路的完整读数报到串口。原始值一起打出来 —— 现场标定门限、核对接线都靠它：
 *     IR   : left  diff=0120  dark=4080  lit=3960  level=NEAR
 * diff = 灭灯读数 - 亮灯读数（反射强度），dark / lit 是 ADC3 原始值。 */
static void ReportIr(const char *tag, const IrResult_t *r)
{
    char    buf[80];
    uint8_t pos = 0;

    AppendTextX(buf, &pos, "IR   : ");
    AppendTextX(buf, &pos, tag);
    AppendTextX(buf, &pos, "  diff=");
    AppendDigits4(buf, &pos, r->diff);
    AppendTextX(buf, &pos, "  dark=");
    AppendDigits4(buf, &pos, r->dark);
    AppendTextX(buf, &pos, "  lit=");
    AppendDigits4(buf, &pos, r->lit);
    AppendTextX(buf, &pos, "  level=");
    AppendTextX(buf, &pos, Ir_LevelWord(r->level));
    AppendTextX(buf, &pos, "\\r\\n");
    buf[pos] = '\\0';

    Usart_SendString(buf);
}

/* 需求5-1：KEY1 单击 —— 完成【左侧】红外的距离测量并显示 */
static void KeyIrLeft(void)
{
    Ir_Measure(1u, &s_irL);             /* 完整测一次：灭灯本底 -> 亮灯反射 */
    s_irLeft       = Ir_IsBlocked(1u);
    s_irLeftValid  = 1u;
    s_line3Mode    = 2u;                /* 第 3、4 行切到红外版式 */
    SetMessage("IR LEFT DONE");
    ReportIr("left ", &s_irL);
    UpdateDisplay();
}

/* 需求5-1：KEY2 单击 —— 完成【右侧】红外的距离测量并显示 */
static void KeyIrRight(void)
{
    Ir_Measure(0u, &s_irR);
    s_irRight      = Ir_IsBlocked(0u);
    s_irRightValid = 1u;
    s_line3Mode    = 2u;
    SetMessage("IR RIGHT DONE");
    ReportIr("right", &s_irR);
    UpdateDisplay();
}

/* 需求5-2：KEY3 单击 —— 左右两路都测一遍，结果通过串口打印到 PC */
static void KeyIrBoth(void)
{
    Ir_MeasureBoth(&s_irL, &s_irR);     /* 串行测，两路发射管不同时亮 */
    s_irLeft       = Ir_IsBlocked(1u);
    s_irRight      = Ir_IsBlocked(0u);
    s_irLeftValid  = 1u;
    s_irRightValid = 1u;
    s_line3Mode    = 2u;
    SetMessage("IR BOTH DONE");

    Usart_SendString("IR   : ----- both sensors measured -----\\r\\n");
    ReportIr("left ", &s_irL);
    ReportIr("right", &s_irR);
    Usart_SendString("IR   : RESULT  L=");
    Usart_SendString(Ir_LevelWord(s_irL.level));
    Usart_SendString("  R=");
    Usart_SendString(Ir_LevelWord(s_irR.level));
    Usart_SendString("   (FAR=CLEAR  MID/NEAR=BLOCKED)\\r\\n");

    /* 再单独给一行"检测到位"的布尔结论，方便上位机直接抓 0/1 */
    Usart_SendString("IR   : DETECT  L=");
    Usart_SendString((s_irLeft != 0u) ? "1" : "0");
    Usart_SendString("  R=");
    Usart_SendString((s_irRight != 0u) ? "1" : "0");
    Usart_SendString("   (1=blocked  0=clear)\\r\\n");

    UpdateDisplay();
}

/* 调试辅助（串口命令 '#'）：把两路接收管的 ADC3 原始值整个打出来，连打两次测量。
 * 用途：
 *   ① 现场标定门限 —— 拿尺子在不同距离各敲一次，看 diff 落在哪一档；
 *   ② 核对接线 —— 遮住哪一路，只有哪一路的 diff 明显变大。 */
static void DumpIrPins(void)
{
    IrResult_t l;
    IrResult_t r;

    SetMessage("IR ADC SCAN");
    UpdateDisplay();

    Ir_MeasureBoth(&l, &r);

    Usart_SendString("IR   : scan  (dark = LED off / lit = LED on / diff = dark - lit)\\r\\n");
    ReportIr("left ", &l);
    ReportIr("right", &r);
    Usart_SendString("IR   : pins  LED_L=PE5 LED_R=PE6  RX_L=PF9(ADC3_IN7) RX_R=PF10(ADC3_IN8)\\r\\n");
}

""")

ls = raw.split("\r\n")
i0 = [i for i, l in enumerate(ls) if "需求5：红外避障 =================" in l]
i1 = [i for i, l in enumerate(ls) if l.startswith("static void HandleKey(KeyEvent ev)")]
if len(i0) != 1 or len(i1) != 1 or i1[0] <= i0[0]:
    print("!! [P7] 段落定位失败 i0=%s i1=%s" % (i0, i1)); sys.exit(1)
ls = ls[:i0[0]] + NEW_BLOCK.split("\r\n") + ls[i1[0]:]
raw = "\r\n".join(ls)
hits.append("P7 需求5 实现段（替换 %d 行 -> %d 行）" % (i1[0] - i0[0], len(NEW_BLOCK.split("\r\n"))))

# ============================================================
# P8. Ir_Init() 调用处注释
# ============================================================
rep(A("    Ir_Init();                      /* 需求5：红外避障对管（PA0 = 左，PA1 = 右）*/\n"),
    A("""    Ir_Init();                      /* 需求5：红外避障（左发PE5 右发PE6 开漏；
                                       左收PF9 右收PF10 -> ADC3_IN7/IN8）*/
"""), "P8 Ir_Init 调用注释")

# ============================================================
# P9. 启动横幅：OLED 行说明 + IR 引脚行
# ============================================================
rep(A('"  \\xB5\\xDA" "4\\xD0\\xD0=\\xD7\\xB4\\xCC\\xAC\\r\\n"'),
    '"  \\xB5\\xDA" "4\\xD0\\xD0=\\xD7\\xB4\\xCC\\xAC/\\xBA\\xEC\\xCD\\xE2\\xC7\\xBF\\xB6\\xC8\\r\\n"',
    "P9a 横幅 OLED 行说明")

rep_line(["IR  : ", "PA0="],
         "    Usart_SendString(" + cstr(
             u"IR  : 板载两路红外避障对管(分立对管): 左发PE5 右发PE6 开漏驱动(低=亮); "
             u"左收PF9 右收PF10 经10K上拉到3V3, 有障碍=低电平, 走ADC3差分测距\r\n") + ");",
         "P9b 横幅 IR 行")

# ============================================================
# 收尾
# ============================================================
assert raw.count("\n") == raw.count("\r\n"), "行尾被破坏"
io.open(MAIN_C, "w", encoding="utf-8", newline="").write(raw)

print("main.c 补丁完成，共 %d 处：" % len(hits))
for h in hits:
    print("   + " + h)
print("字节数：%d -> %d" % (len(orig.encode("utf-8")), len(raw.encode("utf-8"))))

# ---- 回读校验：确认关键字符串都在 ----
back = io.open(MAIN_C, "r", encoding="utf-8", newline="").read()
must = [
    "IR_RX_L_PIN",                      # 不该有（那是驱动里的）—— 用下面的替代
]
checks = [
    ("Ir_LevelWord(s_irL.level)", "屏上距离分级"),
    ("AppendDigits4", "4 位定宽数字"),
    ("Ir_Measure(1u, &s_irL)", "左路测量"),
    ("Ir_Measure(0u, &s_irR)", "右路测量"),
    ("Ir_MeasureBoth(&s_irL, &s_irR)", "两路测量"),
    ("RX_L=PF9(ADC3_IN7) RX_R=PF10(ADC3_IN8)", "横幅引脚说明"),
    ("LED_L=PE5 LED_R=PE6", "横幅引脚说明2"),
    ("有障碍 = 低电平", "逻辑方向注释"),
]
bad = 0
for s, why in checks:
    if s not in back:
        print("!! 回读缺少 [%s]: %s" % (why, s)); bad += 1
for s in ["PA0", "PA1", "IR_LEFT_PIN", "IR_RIGHT_PIN", "Ir_ReadRaw", "反相输出"]:
    if s in back:
        print("!! 回读仍有旧内容: %s" % s); bad += 1
print("回读校验：" + ("全部通过" if bad == 0 else "有 %d 项未通过" % bad))

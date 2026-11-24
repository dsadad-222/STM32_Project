# -*- coding: utf-8 -*-
"""把 main.c 的 OLED 三页版式整段换成 chapter9 的固定三行版式"""
import io
import os

P = r"D:\STM32_Project\FlashRW_Full\App_User\main.c"

s = io.open(P, encoding="utf-8", errors="surrogateescape").read()

START_MARK = "/* ==================== OLED 三页版式"
END_MARK = "static void UpdateDisplay(void)"

i0 = s.find(START_MARK)
if i0 < 0:
    raise SystemExit("!! 找不到起始标记")
i1 = s.find(END_MARK, i0)
if i1 < 0:
    raise SystemExit("!! 找不到 UpdateDisplay")
# UpdateDisplay 以顶格的 "}" 结束（函数内部的大括号都带缩进）
i2 = s.find("\n}\n", i1)
if i2 < 0:
    raise SystemExit("!! 找不到 UpdateDisplay 结尾")
i2 += 3

new_block = '''/* ==================== OLED 固定三行版式 ====================
 * 本任务（chapter9）要求：
 *     第 1 行  内部 FLASH 读出的数据（十六进制）
 *     第 2 行  温度 Temp
 *     第 3 行  外部 FLASH（W25Q64）读出的数据（十六进制）
 *     第 4 行  状态提示（W25Q64 是否在线 / 最近一次操作结果）
 * 不再分页；按任务书要求也不再显示 ADCvalue / Voltage。
 */

/* 第 1 / 3 行：把 FLASH 数据拼成 "IN:0102030405" 这样的十六进制串。
 * 一行 16 个字符，扣掉 "IN:" 3 格还剩 13 格，最多放 6 个字节；
 * 超过 6 字节就只显示前 5 个再补 ".."，保证永远不顶出屏幕。 */
static void BuildFlashLine(char *line, const char *tag,
                           const uint8_t *data, uint8_t len, uint8_t valid)
{
    static const char hex[] = "0123456789ABCDEF";
    uint8_t pos = 0;
    uint8_t shown;
    uint8_t i;

    AppendTextX(line, &pos, tag);

    if ((valid == 0u) || (len == 0u))
    {
        AppendTextX(line, &pos, "--");
        PadLine(line, &pos);
        return;
    }

    shown = (len > 6u) ? 5u : len;

    for (i = 0u; i < shown; i++)
    {
        line[pos++] = hex[(data[i] >> 4) & 0x0Fu];
        line[pos++] = hex[data[i] & 0x0Fu];
    }

    if (len > 6u)
    {
        line[pos++] = '.';
        line[pos++] = '.';
    }

    PadLine(line, &pos);
}

/* 第 2 行：温度。任务书要求这一行只显示 Temp（ADCvalue / Voltage 已取消）*/
static void BuildTempLine(char *line)
{
    char    num[16];
    uint8_t pos = 0;

    AppendTextX(line, &pos, "TEMP ");
    if (s_sample.valid != 0u)
    {
        /* tempX100 是温度×100（36.86℃ = 3686）。FormatFixed 的位数参数指的是
         * "小数位数"，直接传 1 会把 3686 打成 368.6 —— 先四舍五入到温度×10，
         * 再按 1 位小数格式化，才是 "36.9"。 */
        int32_t tempX10 = (s_sample.tempX100 >= 0)
                        ? ((s_sample.tempX100 + 5) / 10)
                        : ((s_sample.tempX100 - 5) / 10);
        FormatFixed(num, tempX10, 1);
        AppendTextX(line, &pos, num);
        AppendTextX(line, &pos, " C");
    }
    else
    {
        AppendTextX(line, &pos, "--.- C");
    }
    PadLine(line, &pos);
}

static void UpdateDisplay(void)
{
    char line[OLED_COL_MAX + 1];

    /* 第 1 行：内部 FLASH 数据 */
    BuildFlashLine(line, "IN:", s_inData, s_inLen, s_inValid);
    OLED_ShowString(0, 0, line);

    /* 第 2 行：温度 */
    BuildTempLine(line);
    OLED_ShowString(0, 1, line);

    /* 第 3 行：外部 FLASH 数据 */
    BuildFlashLine(line, "EX:", s_exData, s_exLen, s_exValid);
    OLED_ShowString(0, 2, line);

    /* 第 4 行：状态 / 提示 */
    OLED_ShowString(0, 3, s_msg);

    OLED_Refresh();
}
'''

s = s[:i0] + new_block + s[i2:]
io.open(P, "w", encoding="utf-8", errors="surrogateescape").write(s)

print("替换完成")
print("  旧片段长度: %d 字符" % (i2 - i0))
print("  新片段长度: %d 字符" % len(new_block))
print("  剩余 PAGE_ 引用:", s.count("PAGE_"))
print("  剩余 s_page 引用:", s.count("s_page"))
print("  剩余 BuildTempInfo:", s.count("BuildTempInfo"), " BuildSensorInfo:", s.count("BuildSensorInfo"), " DrawHeader:", s.count("DrawHeader"))

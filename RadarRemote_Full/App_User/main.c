/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   ADC 内部温度采集 + 串口控制 + OLED 显示 + 呼吸灯（chapter8 综合）
  *
 *          【本任务（chapter8）新增】
 *          1. 芯片内部温度采集：ADC1 的通道 16，每 2 秒采一次；
 *             温度(℃) = {(V25 - Vsense) / Avg_Slope} + 25
 *             V25 = 1.43V，Avg_Slope = 4.3mV/℃
 *             ★ 这里读的是芯片自己的温度（die 温度），不是环境/室内温度。
 *               传感器就集成在芯片内部，天然跟着芯片自身发热走，所以读数
 *               会比房间空气高几度（72MHz 全速运行大约高 5~9℃），这是它的
 *               正常物理特性，不是故障。任务书只要求"采集内部温度并按公式
 *               换算显示"，并没有要求测室温，所以本项目的定位就是
 *               "芯片温度监测"，屏上和串口报的都是芯片温度。
  *          2. KEY2（PG4）按下：左转向灯（红色 LED1 / PG14）进入呼吸灯效果
  *          3. 每次采集完成：把 ADC 原始值、换算后的模拟量、温度值
  *             显示到 OLED，并通过串口发到 PC：
  *                 Current ADC_Value is XXXX
  *                 Current Voltage is XXXX
  *                 Current Temperature is XXXX
  *
  *          【沿用 chapter7 的功能】
  *          - 串口协议帧控制左/右转向灯、蜂鸣器、LED 灯条
  *          - 串口下发文本显示到 OLED
  *          - 状态与文本写内部 Flash，掉电不丢，开机自动恢复
  *
 *  一、OLED 有两个显示页（0.86 寸，128x32 像素，一行 16 个字符）
 *      温度数据页（默认页，每次采样后都会回到这一页）：
 *          +------------------+
 *          | 29.06 C          |  <- 温度，8x8 字模放大 2 倍的大字（16 像素高）
 *          |                  |     占屏幕上半部分，一眼就能看清
 *          | ADC  1738 1.390 V |  <- ADC 原始值 0~4095 + 换算后的模拟量
 *          | L0 R0 B0 D0  CAL  |  <- 设备状态（L左转 R右转 B蜂鸣器 D灯条）+ 尾部标记
 *          +------------------+
 *          之所以把温度单独放大：0.86 寸屏只有 32 像素高，4 行 8x8 小字会把
 *          屏幕顶满、行间毫无空隙，看着很挤也看不清。现在改成"1 行大字 + 2 行小字"，
 *          既腾出了留白，关键数据（温度）也放大了一倍。
 *      文本页（串口下发文本后自动切过来，或按 KEY1 切换）：
 *          第 1、2 行 = 串口发来的 32 个字符，第 3 行 = 提示信息
 *      尾部标记：CAL = 已标定 / BRTH = 呼吸灯在跑 / RST = 开机从 Flash 恢复 / NEW = 首次上电
 *      屏的从机地址上电自动识别（0x78 / 0x7A 都试一遍），开机横幅会打印
 *      "OLED : ack ok ..." 或 "OLED : NO ACK ..."，屏不亮时可据此判断是
 *      接线问题还是驱动问题。
  *
  *  二、按键（按下为低电平）
  *      KEY1(PG3) 单击：切换 OLED 显示页（温度数据页 / 文本页）
  *      KEY2(PG4) 单击：左转向灯呼吸灯 开 / 关
  *      KEY3(PG5) 单击：立即采集一次温度并上报（不用等 2 秒）
  *
  *  三、协议帧格式（与任务书一致）
  *      ┌────────┬────────┬──────────────┬────────────┬──────────────────┐
  *      │ 帧头 0 │ 帧头 1 │  数据域长度  │   功能字   │       数据       │
  *      │  0x55  │  0xFF  │      N       │    见下    │      见下        │
  *      └────────┴────────┴──────────────┴────────────┴──────────────────┘
  *      N = 功能字 + 数据 的字节数。数据后面可以再跟校验字节，
  *          解析器收满自己需要的参数就立刻执行，多出来的字节会被忽略。
  *
  *      0x06  控制设备，数据 = 控制单元 + 开关状态
  *              控制单元：0x00 左转向灯 LED1(PG14)   0x01 右转向灯 LED2(PG15)
  *                        0x02 蜂鸣器   (PG12)       0x03 LED 灯 RGB 灯条(PG0/PG1/PG2)
  *              开关状态：0x00 关，0x01 开（只带 1 个字节的旧格式按"翻转"处理）
  *      0x07  下发文本，数据 = ASCII 文本（最多 32 个字符）
  *            文本显示到 OLED 文本页并写入 Flash
  *      0x08  存储操作，数据 = 操作码（0x00 保存 / 0x01 清除 / 0x02 重新读回）
  *
  *      例子：
  *          55 FF 03 06 02 01     蜂鸣器 开      （...02 00 即关）
  *          55 FF 03 06 00 01     左转向灯 开
  *          55 FF 06 07 HELLO     OLED 显示 "HELLO" 并写入 Flash
  *          55 FF 02 08 01        清除 Flash 记录
  *
 *  四、ASCII 快捷命令（调试用，空闲状态下直接敲，不影响协议帧）
 *      L/R/B/D + 1|0   左转/右转/蜂鸣器/LED 灯 开或关，省略数字 = 翻转
 *      T + 文本        显示到 OLED 并保存（回车结束）
 *      S / C / P       保存 Flash / 清除 Flash / 重新读回
 *      A               立即采集一次温度并上报
 *      K + 温度 + 回车 一键标定：把当前温度当作指定温度（不填数字 = 25℃），
 *                      得到的偏移量写进 Flash，掉电不丢
 *      Z               清除标定，恢复成手册公式的原始结果
 *
 *  五、温度为什么偏高、以及怎么改（重点，汇报时讲这段）
 *
 *      【现象】室温下读数 ~98℃，看着像芯片在发烧。
 *
 *      【第一步先分清：是"真高温"还是"固定偏差"】
 *          看开机瞬间的第一次读数 —— 实测上电一小会儿就已经 96.4℃。
 *          芯片热质量很小但也不可能 1 秒内从室温冲到 96℃，所以这 96℃ 里
 *          绝大部分是**固定零点偏差**，不是真实温度。
 *          之后读数从 96.4 缓慢爬到 98.9℃、噪声只有 ±0.3℃，那 2~3℃ 才是
 *          真实的芯片自热。两个成分要分开看。
 *
 *      【第二步找偏差出在哪】
 *          公式 T = (V25 - Vsense)/Avg_Slope + 25 本身没问题，
 *          偏差只能出在 V25 / Vsense / Avg_Slope 三个量上：
 *            · Vsense = AD值 × VDDA / 4096 —— VDDA 已经用通道 17 的 Vrefint
 *              反推过（实测约 3.13V，落在合理区间内，这一路是准的）；
 *            · 剩下的就是 V25：手册给的是 1.43V「典型值」，芯片之间本来就有
 *              离散性，非原厂的兼容片偏差更大。V25 实测偏低 0.3V，按
 *              4.3mV/℃ 折合就是 70℃ 左右的整体平移 —— 正好对上现象。
 *
 *      【第三步：单点标定把它拉回来】
 *          偏差是**加性**的（整体平移，不改变斜率），所以一个偏移量就能修正：
 *              偏移量 = 参考温度 - 公式算出的温度
 *          在一个已知温度下（比如室温 29℃）敲一次 K，偏移量存进内部 Flash，
 *          以后每次算温度都加上它，掉电不丢。
 *          标定后关机再开的自热趋势依然保留（相对测量一直是准的），
 *          这才是这颗片子真正能给的精度。
 *
 *      【顺带加的两层健壮性】
 *          · 丢首次转换 + 去极值平均：切换通道后第一次转换不可信，丢掉；
 *            连读 8 次再扣掉最大最小各一次，避免野点把结果拉偏。
 *          · VDDA 合理区间放宽到 1800~4600mV：原来卡在 2800~3600mV，
 *            万一供电真的偏离（电池供电、两路电源倒灌抬高），反推值会被
 *            当成坏点退回 3.300V 默认值，温度就会整体算错几十度。
 *            区间放宽后，实测 VDDA 一律参与换算。
 ******************************************************************************
 */

#include "led_drv.h"
#include "beep_drv.h"
#include "systick_drv.h"
#include "usart_drv.h"
#include "oled_drv.h"
#include "flash_drv.h"
#include "adc_drv.h"
#include "key_drv.h"
#include "pwm_drv.h"
#include "cn_msg.h"
#include "hcsr04_drv.h"
#include "nec_ir_drv.h"

/* ========================= 协议字段 ========================= */

#define FRAME_HEAD0         0x55
#define FRAME_HEAD1         0xFF

#define FUNC_CTRL           0x06        /* 控制设备 */
#define FUNC_TEXT           0x07        /* 下发文本 */
#define FUNC_STORE          0x08        /* 存储操作 */

#define CTRL_LEFT_TURN      0x00
#define CTRL_RIGHT_TURN     0x01
#define CTRL_BEEP           0x02
#define CTRL_LED            0x03

#define STORE_OP_SAVE       0x00
#define STORE_OP_CLEAR      0x01
#define STORE_OP_RELOAD     0x02

#define FRAME_DATA_MAX      40          /* 单帧数据域最多 40 字节 */
#define PARSE_TIMEOUT_MS    200         /* 帧内字节间隔超时，丢弃半截帧 */
#define ASCII_TIMEOUT_MS    3000        /* ASCII 快捷命令的超时（人手敲，给宽一点）*/
#define TURN_BLINK_PERIOD   500         /* 转向灯闪烁半周期（ms）*/

/* ========================= 本任务参数 ========================= */

#define SAMPLE_PERIOD_MS    2000u       /* 温度采集周期：2 秒 */
#define VALUE_WIDTH         5u          /* 数值在屏上右对齐的宽度 */

#define PAGE_TEMP           0u          /* OLED 温度数据页 */
#define PAGE_TEXT           1u          /* OLED 文本页 */
#define PAGE_RADAR          2u          /* OLED 倒车雷达页 */
#define PAGE_COUNT          3u          /* 页数（KEY1 循环切换）*/

/* ========================= 倒车雷达参数 ========================= */
/* 距离分级（HC-SR04 量程 2cm~4m，倒车场景只用前 2m）：
 *   无回波/超量程 -> 静音、灯灭（模块没接线时不会乱叫）
 *   >= 100cm       -> 安全 绿 静音
 *    40 ~ 99cm     -> 注意 黄 慢响  80ms 响 / 600ms 停
 *    20 ~ 39cm     -> 接近 黄 快响  80ms 响 / 220ms 停
 *    <  20cm       -> 危险 红 长鸣
 * 有源蜂鸣器只能"响/停"，所以近距的急促感靠"响的时间占比变大"做出来。*/
#define RADAR_ZONE_NONE     0u
#define RADAR_ZONE_SAFE     1u
#define RADAR_ZONE_CARE     2u
#define RADAR_ZONE_CLOSE    3u
#define RADAR_ZONE_DANGER   4u
#define RADAR_ZONE_MAX      5u

#define RADAR_PERIOD_MS     120u        /* 连续测距周期（ms）*/
#define RADAR_LOG_MS        500u        /* 串口上报节流（ms），免得刷屏 */
#define RADAR_BAR_SEG       13u         /* 距离条格子数 */

/* 每级的蜂鸣导通/断开时间；off == 0 表示长鸣，on == 0 表示静音 */
static const uint16_t s_zoneBeepOn[RADAR_ZONE_MAX]  = {   0u,    0u,  80u,  80u, 80u };
static const uint16_t s_zoneBeepOff[RADAR_ZONE_MAX] = {   0u,    0u, 600u, 220u,   0u };
static const RGB_TypeDef s_zoneColor[RADAR_ZONE_MAX] =
{
    RGB_NONE, RGB_G, RGB_YELLOW, RGB_YELLOW, RGB_R
};

/* ========================= 运行状态 ========================= */

static uint8_t      s_leftTurnOn   = 0;
static uint8_t      s_rightTurnOn  = 0;
static uint8_t      s_beepOn       = 0;
static uint8_t      s_ledOn        = 0;
static uint8_t      s_blinkPhase   = 0;
static uint32_t     s_blinkTick    = 0;

/* 右转向灯的彩虹色序：每闪一次换一色 */
#define RAINBOW_STEP_MAX    6u
static const RGB_TypeDef s_rainbow[RAINBOW_STEP_MAX] =
{
    RGB_R, RGB_YELLOW, RGB_G, RGB_CYAN, RGB_B, RGB_MAGENTA
};
static uint8_t      s_rainbowIdx   = 0;

static char         s_text[STORE_TEXT_MAX];     /* 当前文本，定长 32，空格补齐 */
static uint32_t     s_textLen      = 0;         /* 有效字符个数 */
static char         s_msg[OLED_COL_MAX + 1];    /* OLED 文本页第 3 行的提示 */
static uint8_t      s_bootRestored = 0;         /* 本次开机是否从 Flash 恢复 */

static uint8_t      s_page         = PAGE_TEMP; /* 当前显示页 */
static uint32_t     s_lastSampleMs = 0;         /* 上次采样时刻 */
static uint32_t     s_lastKeyMs    = 0;         /* 上次按键扫描时刻 */
static AdcTempSample_t s_sample;                /* 最近一次采样结果 */

/* 倒车雷达运行状态 */
static uint8_t      s_radarOn      = 0;         /* 雷达连续测距模式：1 = 开 */
static uint8_t      s_pageBak      = PAGE_TEMP; /* 进雷达页前的页，关雷达时还原 */
static uint32_t     s_radarTick    = 0;         /* 上次测距时刻 */
static uint32_t     s_radarLogTick = 0;         /* 上次串口上报时刻 */
static uint32_t     s_radarBeepTick= 0;         /* 蜂鸣节奏切换时刻 */
static uint8_t      s_radarBuzzing = 0;         /* 蜂鸣器当前是否在响 */
static uint8_t      s_radarZone    = RADAR_ZONE_NONE;
static uint16_t     s_radarMm      = 0xFFFFu;   /* 最近一次距离（mm），0xFFFF = 无回波 */

/* 协议解析状态机 */
typedef enum
{
    RX_HEAD0 = 0,       /* 等帧头 0x55（空闲态同时识别 ASCII 快捷命令）*/
    RX_HEAD1,           /* 等帧头 0xFF */
    RX_LEN,             /* 等数据域长度 */
    RX_FUNC,            /* 等功能字 */
    RX_DATA,            /* 收数据 */
    RX_ASCII_ARG,       /* 快捷命令：等 '0'/'1'（等不到就翻转一次）*/
    RX_ASCII_TEXT,      /* 快捷命令：收文本，回车/换行或满 32 字符结束 */
    RX_ASCII_CAL        /* 快捷命令 K：收标定参考温度，回车/换行结束 */
} RxState_t;

static RxState_t    s_rxState    = RX_HEAD0;
static uint8_t      s_rxLen      = 0;           /* 长度域声明的值 */
static uint8_t      s_rxFunc     = 0;           /* 本次帧的功能字 */
static uint8_t      s_rxNeed     = 0;           /* 还差几个数据字节 */
static uint8_t      s_rxCount    = 0;           /* 已收数据字节数 */
static uint8_t      s_rxData[FRAME_DATA_MAX];
static uint32_t     s_lastRxMs   = 0;
static uint8_t      s_asciiCmd   = 0;           /* 快捷命令首字母 L/R/B/D */
static uint32_t     s_calRefC    = 0;           /* K 命令收到的参考温度整数部分（℃）*/

static StoreRecord_t s_saved;                   /* 最近一次写入 / 读出的记录 */

/* ========================= 数字格式化 ========================= */

static uint8_t StrLen(const char *str)
{
    uint8_t n = 0;

    while (str[n] != '\0')
    {
        n++;
    }
    return n;
}

/* 无符号整数转十进制字符串，返回写入的字符个数 */
static uint8_t WriteU32(char *out, uint32_t value)
{
    char    tmp[10];
    uint8_t n = 0;
    uint8_t i;

    if (value == 0u)
    {
        out[0] = '0';
        return 1u;
    }

    while ((value > 0u) && (n < 10u))
    {
        tmp[n] = (char)('0' + (value % 10u));
        value /= 10u;
        n++;
    }

    for (i = 0; i < n; i++)
    {
        out[i] = tmp[n - 1u - i];
    }
    return n;
}

/* 把放大 10^decimals 倍的整数写成小数文本，例如 (1626, 3) -> "1.626" */
static void FormatFixed(char *out, int32_t scaled, uint8_t decimals)
{
    uint32_t div = 1u;
    uint32_t frac;
    int32_t  intPart;
    uint8_t  i;

    for (i = 0; i < decimals; i++)
    {
        div *= 10u;
    }

    if (scaled < 0)
    {
        *out = '-';
        out++;
        scaled = -scaled;
    }

    intPart = scaled / (int32_t)div;
    frac    = (uint32_t)(scaled % (int32_t)div);

    out += WriteU32(out, (uint32_t)intPart);

    if (decimals > 0u)
    {
        uint32_t p = div / 10u;

        *out = '.';
        out++;
        while (p > 0u)
        {
            *out = (char)('0' + ((frac / p) % 10u));
            out++;
            p /= 10u;
        }
    }

    *out = '\0';
}

/* 把数值右对齐写进 line 的固定宽度区域，屏幕上的数字不会左右跳动 */
static void AppendValue(char *line, uint8_t *pos, int32_t scaled, uint8_t decimals)
{
    char    num[16];
    uint8_t n;
    uint8_t i;

    FormatFixed(num, scaled, decimals);
    n = StrLen(num);

    for (i = n; i < VALUE_WIDTH; i++)
    {
        line[*pos] = ' ';
        (*pos)++;
    }
    for (i = 0; i < n; i++)
    {
        line[*pos] = num[i];
        (*pos)++;
    }
}

static void AppendTextX(char *line, uint8_t *pos, const char *text)
{
    uint8_t i = 0;

    while (text[i] != '\0')
    {
        line[*pos] = text[i];
        (*pos)++;
        i++;
    }
}

static void PadLine(char *line, uint8_t *pos)
{
    while (*pos < OLED_COL_MAX)
    {
        line[*pos] = ' ';
        (*pos)++;
    }
    line[*pos] = '\0';
}

/* ========================= 显示 ========================= */

static void SetMessage(const char *text)
{
    uint8_t i = 0;

    while ((i < OLED_COL_MAX) && (text[i] != '\0'))
    {
        s_msg[i] = text[i];
        i++;
    }
    while (i < OLED_COL_MAX)
    {
        s_msg[i] = ' ';
        i++;
    }
    s_msg[OLED_COL_MAX] = '\0';
}

static void TextFillSpace(void)
{
    uint32_t i;

    for (i = 0; i < STORE_TEXT_MAX; i++)
    {
        s_text[i] = ' ';
    }
    s_textLen = 0;
}

/* 第 4 行：设备状态 + 模式提示 */
static void BuildStatusLine(char *line)
{
    uint8_t pos = 0;

    line[pos++] = 'L';
    line[pos++] = (s_leftTurnOn  != 0) ? '1' : '0';
    line[pos++] = ' ';
    line[pos++] = 'R';
    line[pos++] = (s_rightTurnOn != 0) ? '1' : '0';
    line[pos++] = ' ';
    line[pos++] = 'B';
    line[pos++] = (s_beepOn      != 0) ? '1' : '0';
    line[pos++] = ' ';
    line[pos++] = 'D';
    line[pos++] = (s_ledOn       != 0) ? '1' : '0';

    /* 尾部 5 格提示当前状态：已标定 / 呼吸灯 / 文本页 / 开机来源 */
    if (Adc_GetCalOffsetX100() != 0)
    {
        AppendTextX(line, &pos, " CAL ");
    }
    else if (Breath_IsActive() != 0)
    {
        AppendTextX(line, &pos, "BRTH ");
    }
    else if (s_page == PAGE_TEXT)
    {
        AppendTextX(line, &pos, "TEXT ");
    }
    else if (s_bootRestored != 0)
    {
        AppendTextX(line, &pos, " RST ");
    }
    else
    {
        AppendTextX(line, &pos, " NEW ");
    }

    PadLine(line, &pos);
}

/* 温度页大字行的数值部分（col 3 起）："35.9C"，5 个字符正好占满右半屏。
 * col 0-1 由“温度”两个 16x16 汉字占用，col 2 留空做间隔。 */
static void BuildTempBig(char *line)
{
    if (s_sample.valid != 0u)
    {
        FormatFixed(line, s_sample.tempX100, 1);        /* 例 "35.9"（一位小数够用）*/
    }
    else
    {
        line[0] = '-';
        line[1] = '-';
        line[2] = '.';
        line[3] = '-';
        line[4] = '\0';                                 /* 读数不可信：屏上显示 --.- */
    }

    if (StrLen(line) > 4u)
    {
        line[4] = '\0';                                 /* 保险：数值最多 4 个字符 */
    }
    line[StrLen(line)] = 'C';
    line[StrLen(line) + 1u] = '\0';
}

/* 温度页第 2 行：ADC 原始值（左） + 换算后的模拟量（右），定宽右对齐，数字不会左右抖 */
static void BuildSampleLine2(char *line)
{
    uint8_t pos = 0;

    AppendTextX(line, &pos, "ADC");
    AppendValue(line, &pos, (int32_t)s_sample.rawValue, 0);
    AppendTextX(line, &pos, " ");
    AppendValue(line, &pos, (int32_t)s_sample.voltageMv, 3);    /* mV -> V，3 位小数 */
    AppendTextX(line, &pos, " V");
    PadLine(line, &pos);
}

/* ========================= 倒车雷达页的显示 ========================= */

/* 距离(mm) -> 分级 */
static uint8_t RadarZoneOf(uint16_t mm)
{
    if (mm == 0xFFFFu)  { return RADAR_ZONE_NONE;   }   /* 超时/超量程 */
    if (mm < 200u)      { return RADAR_ZONE_DANGER; }
    if (mm < 400u)      { return RADAR_ZONE_CLOSE;  }
    if (mm < 1000u)     { return RADAR_ZONE_CARE;   }
    return RADAR_ZONE_SAFE;
}

/* 分级 -> OLED 上的两个汉字（GBK 双字节）*/
static const char *RadarZoneMsg(uint8_t zone)
{
    switch (zone)
    {
        case RADAR_ZONE_SAFE:   return CN_R_SAFE;    /* 安全 */
        case RADAR_ZONE_CARE:   return CN_R_CARE;    /* 注意 */
        case RADAR_ZONE_CLOSE:  return CN_R_CLOSE;   /* 接近 */
        case RADAR_ZONE_DANGER: return CN_R_DANGER;  /* 危险 */
        default:                return CN_R_NOECHO;  /* 无回波 */
    }
}

/* 大字行的数值部分："173CM"，无回波时 "---CM" */
static void BuildRadarBig(char *line)
{
    uint32_t cm;
    uint8_t  n;

    if (s_radarMm == 0xFFFFu)
    {
        line[0] = '-'; line[1] = '-'; line[2] = '-';
        line[3] = 'C'; line[4] = 'M'; line[5] = '\0';
        return;
    }

    cm = ((uint32_t)s_radarMm + 5u) / 10u;      /* mm -> cm，四舍五入 */
    if (cm > 400u) { cm = 400u; }               /* 展示上限 4m，和量程一致 */
    n  = WriteU32(line, cm);
    line[n]     = 'C';
    line[n + 1u] = 'M';
    line[n + 2u] = '\0';
}

/* 第 3 行（col 3 起）：距离条，越近格子越多，13 格 = 2m 满格 */
static void BuildRadarBar(char *line)
{
    uint32_t mm = (s_radarMm == 0xFFFFu) ? 2000u : (uint32_t)s_radarMm;
    uint8_t  lit;
    uint8_t  i;

    if (mm > 2000u) { mm = 2000u; }
    lit = (uint8_t)(((2000u - mm) * RADAR_BAR_SEG) / 2000u);

    for (i = 0; i < RADAR_BAR_SEG; i++)
    {
        line[i] = (i < lit) ? '#' : '-';
    }
    line[RADAR_BAR_SEG] = '\0';
}

/* 第 4 行：蜂鸣节奏 + 原始毫米值（便于和卷尺核对）*/
static void BuildRadarLine3(char *line)
{
    uint8_t pos = 0;

    AppendTextX(line, &pos, "BEEP:");
    if (s_radarOn == 0u)
    {
        AppendTextX(line, &pos, "IDLE");
    }
    else if (s_radarZone == RADAR_ZONE_NONE)
    {
        AppendTextX(line, &pos, "NONE");
    }
    else if (s_radarZone == RADAR_ZONE_SAFE)
    {
        AppendTextX(line, &pos, "OFF ");
    }
    else if (s_radarZone == RADAR_ZONE_CARE)
    {
        AppendTextX(line, &pos, "SLOW");
    }
    else if (s_radarZone == RADAR_ZONE_CLOSE)
    {
        AppendTextX(line, &pos, "FAST");
    }
    else
    {
        AppendTextX(line, &pos, "STOP");
    }

    line[pos++] = ' ';
    if (s_radarMm == 0xFFFFu)
    {
        AppendTextX(line, &pos, "---MM");
    }
    else
    {
        pos = (uint8_t)(pos + WriteU32(&line[pos], (uint32_t)s_radarMm));
        AppendTextX(line, &pos, "MM");
    }
    PadLine(line, &pos);
}

static void UpdateDisplay(void)
{
    char    line[OLED_COL_MAX + 1];
    char    line2[OLED_COL_MAX + 1];
    char    bigLine[OLED_BIG_COL_MAX + 8];
    uint8_t i;
    uint8_t cnLen;
    uint8_t startCol;

    if (s_page == PAGE_TEXT)
    {
        /* 文本页：第 1、2 行放 32 个字符（16 x 2），下面两行放中文提示（16x16 大字居中）*/
        OLED_ClearLine(0);
        OLED_ClearLine(1);
        for (i = 0; i < OLED_COL_MAX; i++)
        {
            OLED_ShowChar(i, 0, s_text[i]);
            OLED_ShowChar(i, 1, s_text[OLED_COL_MAX + i]);
        }
        OLED_ClearLine(2);
        OLED_ClearLine(3);

        cnLen = (uint8_t)(StrLen(s_msg) / 2u);          /* GBK 两个字节是一个汉字 */
        if (cnLen > OLED_BIG_COL_MAX)
        {
            cnLen = OLED_BIG_COL_MAX;
        }
        startCol = (uint8_t)((OLED_BIG_COL_MAX - cnLen) / 2u);
        OLED_ShowCNString(startCol, 2, s_msg);
    }
    else if (s_page == PAGE_RADAR)
    {
        /* 倒车雷达页：上半屏 “距离”+大字厘米数，第 3 行分级汉字 + 距离条，第 4 行蜂鸣节奏 */
        BuildRadarBig(bigLine);
        BuildRadarBar(line2);
        BuildRadarLine3(line);

        OLED_ClearLine(0);
        OLED_ClearLine(1);
        OLED_ClearLine(2);
        OLED_ClearLine(3);

        OLED_ShowCNString(0, 0, CN_R_DIST);             /* col 0-1：距离 */
        startCol = (uint8_t)(OLED_BIG_COL_MAX - StrLen(bigLine));
        if (startCol < 2u) { startCol = 2u; }           /* 不压到左边的汉字 */
        OLED_ShowStringBig(startCol, 0, bigLine);       /* 数值右对齐 + CM */

        OLED_ShowCNString(0, 2, RadarZoneMsg(s_radarZone));
        OLED_ShowString(3, 2, line2);                   /* col 3 起：距离条 */
        OLED_ShowString(0, 3, line);
    }
    else
    {
        /* 温度数据页：上半屏大字 = “温度” + 数值（跨第 0/1 页），第 3 行放 ADC 值和电压 */
        BuildTempBig(bigLine);
        BuildSampleLine2(line2);

        OLED_ClearLine(0);
        OLED_ClearLine(1);
        OLED_ClearLine(2);
        OLED_ShowCNString(0, 0, CN_TEMP);               /* col 0-1：温度两个汉字 */
        OLED_ShowStringBig(3, 0, bigLine);              /* col 3-7：数值 + C */
        OLED_ShowString(0, 2, line2);

        /* 最后一页：设备状态（温度页才显示；文本页这两行让给中文提示）*/
        BuildStatusLine(line);
        OLED_ClearLine(3);
        OLED_ShowString(0, 3, line);
    }

    OLED_Refresh();
}

/* ========================= 温度采集与上报 ========================= */

/* 串口上报格式（任务书要求的三行）：
 *     Current ADC_Value is XXXX
 *     Current Voltage is XXXX
 *     Current Temperature is XXXX
 */
static void ReportSample(void)
{
    char num[16];

    Usart_SendString("Current ADC_Value is ");
    FormatFixed(num, (int32_t)s_sample.rawValue, 0);
    Usart_SendString(num);
    Usart_SendString("\r\n");

    Usart_SendString("Current Voltage is ");
    FormatFixed(num, (int32_t)s_sample.voltageMv, 3);
    Usart_SendString(num);
    Usart_SendString("\r\n");

    Usart_SendString("Current Temperature is ");
    if (s_sample.valid != 0u)
    {
        FormatFixed(num, s_sample.tempX100, 2);
        Usart_SendString(num);
    }
    else
    {
        /* -40~125℃ 之外认为读数不可信（例如 TSVREFE 没打开、通道读回 0），
           不把离谱数字当真值报出去 */
        Usart_SendString("--");
    }
    Usart_SendString("\r\n");

    /* 第 4 行是诊断信息。温度算得准不准全看 VDDA 取得对不对，
       所以把本次换算用的 VDDA 和 Vrefint 原始值一并打出来：
       正常板子 VDDA 应在 3.2~3.4V 附近；如果显示 4.2V 之类，说明供电偏高。*/
    Usart_SendString("Current VDDA is ");
    FormatFixed(num, (int32_t)s_sample.vddaMv, 0);
    Usart_SendString(num);
    Usart_SendString(" mV (Vrefint raw ");
    FormatFixed(num, (int32_t)s_sample.vrefRaw, 0);
    Usart_SendString(num);
    Usart_SendString(")\r\n");

    if (s_sample.vddaMv > ADC_VDDA_MV_WARN)
    {
        Usart_SendString("WARN : " CN_VDDA_WARN " (VDDA > 3.7V)\r\n");
    }

    /* 中文摘要行：任务书要求的三行英文格式原样保留在上面，这一行只是给人看的，
       一眼读懂本次采样结果；标定状态也放在这里说（省得每 2 秒再刷一行 CAL）*/
    Usart_SendString(CN_SUMMARY " : " CN_TEMP " ");
    if (s_sample.valid != 0u)
    {
        FormatFixed(num, s_sample.tempX100, 2);
        Usart_SendString(num);
    }
    else
    {
        Usart_SendString("--");
    }
    Usart_SendString(" C   " CN_VOLT " ");
    FormatFixed(num, (int32_t)s_sample.voltageMv, 3);
    Usart_SendString(num);
    Usart_SendString(" V   " CN_RAWVAL " ");
    FormatFixed(num, (int32_t)s_sample.rawValue, 0);
    Usart_SendString(num);
    Usart_SendString("   " CN_DIE_TEMP " (");
    Usart_SendString((Adc_GetCalOffsetX100() != 0) ? CN_CALED : CN_UNCAL);
    Usart_SendString(")\r\n");

    /* 呼吸灯诊断：duty 应在 0~100 之间来回走（主循环在调），
       cnt 应一直在变（TIM2 中断在跑）。两样都动 = 软件链路正常 */
    if (Breath_IsActive() != 0u)
    {
        Usart_SendString("BREATH duty=");
        FormatFixed(num, (int32_t)Breath_GetDuty(), 0);
        Usart_SendString(num);
        Usart_SendString("/100 cnt=");
        FormatFixed(num, (int32_t)Breath_GetPwmCnt(), 0);
        Usart_SendString(num);
        Usart_SendString("\r\n");
    }
}

/* 采一次 -> 串口上报 -> 刷到 OLED（采样后总是回到温度数据页）*/
static void DoSample(void)
{
    Adc_SampleTemp(&s_sample);
    ReportSample();
    s_page = PAGE_TEMP;
    UpdateDisplay();
}

/* ========================= 设备控制 ========================= */

static void ReportState(void)
{
    Usart_SendString("STATUS  LEFT_TURN=");
    Usart_SendString((s_leftTurnOn  != 0) ? "ON" : "OFF");
    Usart_SendString("  RIGHT_TURN=");
    Usart_SendString((s_rightTurnOn != 0) ? "ON" : "OFF");
    Usart_SendString("  BEEP=");
    Usart_SendString((s_beepOn      != 0) ? "ON" : "OFF");
    Usart_SendString("  LED=");
    Usart_SendString((s_ledOn       != 0) ? "ON" : "OFF");
    Usart_SendString("  BREATH=");
    Usart_SendString((Breath_IsActive() != 0) ? "ON" : "OFF");
    Usart_SendString("\r\n");
}

static void ApplyHardware(void)
{
    uint32_t now = Get_SysRunTime();

    /* 呼吸模式下 PG14 由 TIM2 中断独占，这里绝不能碰，否则会把 PWM 盖成常亮 */
    if (Breath_IsActive() == 0u)
    {
        if (s_leftTurnOn != 0)
        {
            s_blinkPhase = 1;               /* 开启后立刻点亮，不等第一个闪烁周期 */
            s_blinkTick  = now;
            LED_On(LED1);
        }
        else
        {
            LED_Off(LED1);
        }
    }

    if (s_rightTurnOn != 0)
    {
        s_blinkPhase = 1;
        s_blinkTick  = now;
        LED_On(LED2);
        RGB2_Set(RGB_R);                /* 右灯珠（PE2/3/4）先点亮红色，随后由闪烁服务变色 */
    }
    else
    {
        LED_Off(LED2);
        RGB2_Set(RGB_NONE);
    }

    if (s_beepOn != 0)
    {
        Beep_On();
    }
    else
    {
        Beep_Off();
    }

    /* 灯条（RGB）在呼吸模式下由 TIM2 中断同步驱动，这里不要抢 */
    if (Breath_IsActive() == 0u)
    {
        RGB_Set((s_ledOn != 0) ? RGB_ALL : RGB_NONE);
    }
}

/* 转向灯闪烁。注意：左转向灯正在呼吸时由呼吸灯模块独占 PG14，这里不碰它 */
static void TurnSignalService(void)
{
    uint32_t now = Get_SysRunTime();
    uint8_t  phase;
    uint8_t  breath = Breath_IsActive();

    if ((s_leftTurnOn == 0) && (s_rightTurnOn == 0))
    {
        s_blinkTick = now;
        return;
    }

    if ((uint32_t)(now - s_blinkTick) < TURN_BLINK_PERIOD)
    {
        return;
    }

    s_blinkTick  = now;
    s_blinkPhase = (uint8_t)(!s_blinkPhase);
    phase        = s_blinkPhase;

    if (breath == 0u)
    {
        if (s_leftTurnOn != 0)
        {
            if (phase != 0) { LED_On(LED1); } else { LED_Off(LED1); }
        }
        else
        {
            LED_Off(LED1);
        }
    }

    if (s_rightTurnOn != 0)
    {
        if (phase != 0)
        {
            LED_On(LED2);
            /* 右灯珠彩虹闪烁：每亮一次换一种颜色，红→黄→绿→青→蓝→紫轮转 */
            RGB2_Set(s_rainbow[s_rainbowIdx]);
            s_rainbowIdx = (uint8_t)((s_rainbowIdx + 1u) % RAINBOW_STEP_MAX);
        }
        else
        {
            LED_Off(LED2);
            RGB2_Set(RGB_NONE);
        }
    }
    else
    {
        LED_Off(LED2);
        RGB2_Set(RGB_NONE);
    }
}

/* ========================= 呼吸灯 ========================= */

static void ToggleBreath(void)
{
    if (Breath_IsActive() != 0)
    {
        Breath_Stop();
        ApplyHardware();                /* 灯条交回状态控制 */
        SetMessage(CN_BREATH_OFF);
        Usart_SendString("BREATH: off\r\n");
    }
    else
    {
        Breath_Start();
        SetMessage(CN_BREATH_ON);
        Usart_SendString("BREATH: on (LED1 PG14 + RGB lamp together)\r\n");
    }

    ReportState();
    UpdateDisplay();
}

/* ========================= 掉电保存 ========================= */

static void BuildRecord(StoreRecord_t *rec)
{
    uint32_t flags = 0u;
    uint32_t i;

    if (s_leftTurnOn  != 0) { flags |= STORE_BIT_LEFT;  }
    if (s_rightTurnOn != 0) { flags |= STORE_BIT_RIGHT; }
    if (s_beepOn      != 0) { flags |= STORE_BIT_BEEP;  }
    if (s_ledOn       != 0) { flags |= STORE_BIT_LED;   }

    rec->magic         = STORE_MAGIC;
    rec->flags         = flags;
    rec->textLen       = s_textLen;
    rec->calOffsetX100 = (int16_t)Adc_GetCalOffsetX100();   /* 温度标定值一起存 */
    rec->checksum      = 0u;

    for (i = 0; i < STORE_TEXT_MAX; i++)
    {
        rec->text[i] = s_text[i];
    }
}

static void ApplyRecord(const StoreRecord_t *rec)
{
    uint32_t i;

    s_leftTurnOn  = (uint8_t)(((rec->flags & STORE_BIT_LEFT)  != 0u) ? 1 : 0);
    s_rightTurnOn = (uint8_t)(((rec->flags & STORE_BIT_RIGHT) != 0u) ? 1 : 0);
    s_beepOn      = (uint8_t)(((rec->flags & STORE_BIT_BEEP)  != 0u) ? 1 : 0);
    s_ledOn       = (uint8_t)(((rec->flags & STORE_BIT_LED)   != 0u) ? 1 : 0);

    for (i = 0; i < STORE_TEXT_MAX; i++)
    {
        s_text[i] = rec->text[i];
    }
    s_textLen = (rec->textLen <= STORE_TEXT_MAX) ? rec->textLen : STORE_TEXT_MAX;

    Adc_SetCalOffsetX100(rec->calOffsetX100);               /* 恢复上次的标定值 */

    ApplyHardware();
}

/* 内容没变就不重复擦写，省 Flash 寿命。返回 1 = Flash 里已经是当前内容 */
static uint8_t SaveCurrent(void)
{
    StoreRecord_t rec;

    BuildRecord(&rec);

    if ((s_saved.magic == STORE_MAGIC) && (Store_IsSame(&rec, &s_saved) != 0))
    {
        return 1;                   /* 已经存过了，不用再擦写一次 */
    }

    if (Store_Save(&rec) != 0)
    {
        s_saved = rec;
        Usart_SendString("FLASH: saved\r\n");
        return 1;
    }

    Usart_SendString("FLASH: write failed\r\n");
    return 0;
}

/* ========================= 命令处理 ========================= */

static void ExecuteControl(uint8_t code, uint8_t on)
{
    on = (on != 0u) ? 1u : 0u;

    switch (code)
    {
        case CTRL_LEFT_TURN:
            if (Breath_IsActive() != 0)
            {
                Breath_Stop();      /* 手动控制左转向灯时先退出呼吸模式 */
            }
            s_leftTurnOn = on;
            if (on != 0) { s_blinkPhase = 1; s_blinkTick = Get_SysRunTime(); LED_On(LED1); }
            else         { LED_Off(LED1); }
            break;

        case CTRL_RIGHT_TURN:
            s_rightTurnOn = on;
            if (on != 0) { s_blinkPhase = 1; s_blinkTick = Get_SysRunTime(); LED_On(LED2); }
            else         { LED_Off(LED2); }
            break;

        case CTRL_BEEP:
            s_beepOn = on;
            if (on != 0) { Beep_On(); } else { Beep_Off(); }
            break;

        case CTRL_LED:
            s_ledOn = on;
            RGB_Set((on != 0) ? RGB_ALL : RGB_NONE);
            break;

        default:
            SetMessage(CN_BAD_CODE);
            Usart_SendString("ERROR: unknown control code\r\n");
            UpdateDisplay();
            return;
    }

    if (SaveCurrent() != 0)     /* 状态变了就写进 Flash，下次开机自动恢复 */
    {
        SetMessage(CN_CTRL_OK);
    }
    else
    {
        SetMessage(CN_FLASH_ERR);
    }
    ReportState();
    UpdateDisplay();
}

static void HandleText(const uint8_t *data, uint8_t len)
{
    char    log[STORE_TEXT_MAX + 1];
    uint8_t n = len;
    uint8_t i;

    if (n > STORE_TEXT_MAX)
    {
        n = (uint8_t)STORE_TEXT_MAX;
    }

    for (i = 0; i < n; i++)
    {
        char c = (char)data[i];
        /* 不可显示的字符（回车、换行等）用点代替，避免屏上出现乱码 */
        s_text[i] = ((c >= 0x20) && (c <= 0x7E)) ? c : '.';
        log[i]    = s_text[i];
    }
    log[n] = '\0';

    for (i = n; i < STORE_TEXT_MAX; i++)
    {
        s_text[i] = ' ';
    }
    s_textLen = n;

    Usart_SendString("TEXT : ");
    Usart_SendString(log);
    Usart_SendString("\r\n");

    if (SaveCurrent() != 0)     /* 串口下发的文本立刻存进 Flash */
    {
        SetMessage(CN_SAVED);
    }
    else
    {
        SetMessage(CN_FLASH_ERR);
    }

    s_page = PAGE_TEXT;         /* 切到文本页让用户马上看到刚下发的文字 */
    UpdateDisplay();
}

static void HandleStore(uint8_t op)
{
    StoreRecord_t rec;

    switch (op)
    {
        case STORE_OP_SAVE:
            BuildRecord(&rec);
            if (Store_Save(&rec) != 0)
            {
                s_saved = rec;
                SetMessage(CN_SAVED);
                Usart_SendString("FLASH: saved\r\n");
            }
            else
            {
                SetMessage(CN_FLASH_ERR);
                Usart_SendString("FLASH: write failed\r\n");
            }
            break;

        case STORE_OP_CLEAR:
            Store_Clear();
            s_saved.magic = 0u;     /* 清掉缓存，让下一次保存一定会真正写 */
            SetMessage(CN_CLEARED);
            Usart_SendString("FLASH: cleared\r\n");
            break;

        case STORE_OP_RELOAD:
            if (Store_Load(&rec) != 0)
            {
                ApplyRecord(&rec);
                s_saved = rec;
                SetMessage(CN_BOOT_FLASH);
                Usart_SendString("FLASH: reloaded\r\n");
            }
            else
            {
                SetMessage(CN_NO_FLASH);
                Usart_SendString("FLASH: no valid record\r\n");
            }
            break;

        default:
            SetMessage(CN_BAD_CODE);
            Usart_SendString("ERROR: unknown store code\r\n");
            break;
    }

    ReportState();
    UpdateDisplay();
}

/* ======================= 温度单点标定 ======================= */

/* 把"当前实测温度"标定成参考温度，得到的偏移量存进 Flash
 * refC = 0 表示用户没填数字，按默认参考温度（25℃）处理 */
static void DoCalibrate(uint32_t refC)
{
    int32_t rawTempX100;
    int32_t offsetX100;
    char    num[16];

    if ((refC == 0u) || (refC > 99u))
    {
        refC = (uint32_t)(ADC_CAL_REF_X100 / 100);      /* 默认 25℃ */
    }

    Adc_SampleTemp(&s_sample);                          /* 先取一组最新读数 */

    /* 本次读数本身就不在传感器量程内（通道读回 0 / 满量程），标定没有意义，
       拒绝标定，免得把一个坏读数固化进 Flash */
    if (s_sample.valid == 0u)
    {
        Usart_SendString("CAL  : skipped, current sample is invalid\r\n");
        SetMessage(CN_CAL_SKIP);
        UpdateDisplay();
        return;
    }

    /* 注意：这里必须用"不含标定偏移"的公式结果，否则重复按 K 会越标越歪 */
    rawTempX100 = Adc_RawToTempX100(s_sample.rawValue, s_sample.vddaMv);
    offsetX100  = ((int32_t)refC * 100) - rawTempX100;

    /* 偏移量要存进 int16 字段，这里夹一下，防止异常读数把值撑爆
       （Adc_SetCalOffsetX100 内部也会再夹一次，双保险）*/
    if (offsetX100 >  ADC_CAL_OFFSET_X100_LIMIT) { offsetX100 =  ADC_CAL_OFFSET_X100_LIMIT; }
    if (offsetX100 < -ADC_CAL_OFFSET_X100_LIMIT) { offsetX100 = -ADC_CAL_OFFSET_X100_LIMIT; }

    Adc_SetCalOffsetX100(offsetX100);

    Usart_SendString("CAL  : reference ");
    FormatFixed(num, (int32_t)refC * 100, 2);
    Usart_SendString(num);
    Usart_SendString(" C, formula gave ");
    FormatFixed(num, rawTempX100, 2);
    Usart_SendString(num);
    Usart_SendString(" C, offset ");
    FormatFixed(num, offsetX100, 2);
    Usart_SendString(num);
    Usart_SendString(" C\r\n");
    Usart_SendString("       " CN_CAL_OK "\r\n");

    if (SaveCurrent() != 0)
    {
        SetMessage(CN_CAL_OK);
    }
    else
    {
        SetMessage(CN_FLASH_ERR);
    }

    s_page = PAGE_TEMP;
    DoSample();                                         /* 立刻按标定后的结果重采并上报 */
}

/* 清除标定，回到手册公式的原始结果 */
static void DoClearCal(void)
{
    Adc_SetCalOffsetX100(0);

    Usart_SendString("CAL  : cleared\r\n");
    Usart_SendString("       " CN_CAL_CLEAR "\r\n");

    if (SaveCurrent() != 0)
    {
        SetMessage(CN_CAL_CLEAR);
    }
    else
    {
        SetMessage(CN_FLASH_ERR);
    }

    s_page = PAGE_TEMP;
    DoSample();
}

/* 查询某控制单元当前状态（供旧格式"翻转"语义换算目标状态用） */
static uint8_t CurrentOf(uint8_t code)
{
    switch (code)
    {
        case CTRL_LEFT_TURN:  return s_leftTurnOn;
        case CTRL_RIGHT_TURN: return s_rightTurnOn;
        case CTRL_BEEP:       return s_beepOn;
        case CTRL_LED:        return s_ledOn;
        default:              return 0u;
    }
}

/* 一帧收齐，按功能字分发 */
static void DispatchFrame(void)
{
    switch (s_rxFunc)
    {
        case FUNC_CTRL:
            if (s_rxCount >= 2u)
            {
                /* 课件协议表格式：控制单元 + 开关状态(0x00 关 / 0x01 开) */
                ExecuteControl(s_rxData[0], s_rxData[1]);
            }
            else if (s_rxCount == 1u)
            {
                /* 旧格式（单数据字节）：按"翻转一次"处理 */
                ExecuteControl(s_rxData[0], (uint8_t)(!CurrentOf(s_rxData[0])));
            }
            else
            {
                SetMessage(CN_BAD_CODE);
                Usart_SendString("ERROR: missing control unit\r\n");
                UpdateDisplay();
            }
            break;

        case FUNC_TEXT:
            HandleText(s_rxData, s_rxCount);
            break;

        case FUNC_STORE:
            HandleStore(s_rxData[0]);
            break;

        default:
            SetMessage(CN_BAD_CODE);
            Usart_SendString("ERROR: unknown func code\r\n");
            UpdateDisplay();
            break;
    }
}

/* ========================= 协议解析 ========================= */

static void ParserReset(void)
{
    s_rxState = RX_HEAD0;
    s_rxLen   = 0;
    s_rxFunc  = 0;
    s_rxNeed  = 0;
    s_rxCount = 0;
}

/* 快捷命令首字母 -> 控制单元 */
static uint8_t AsciiCodeOf(uint8_t letter)
{
    switch (letter)
    {
        case 'L': return CTRL_LEFT_TURN;
        case 'R': return CTRL_RIGHT_TURN;
        case 'B': return CTRL_BEEP;
        case 'D': return CTRL_LED;
        default:  return 0xFFu;
    }
}

/* 逐字节喂入解析状态机 */
static void DoRadarOnce(void);          /* 超声波测距（定义在按键处理区之前） */
static void ToggleRadar(void);          /* 倒车雷达连续测距 开/关 */

static void ParseByte(uint8_t byte)
{
    uint32_t now = Get_SysRunTime();
    uint32_t timeout;

    /* 帧内字节间隔超时 -> 半截帧作废，重新找帧头。
       ASCII 快捷命令是人手敲的，两个字符之间可能隔上好几秒（比如先敲 K 再按回车），
       所以这几个状态用更宽松的超时，免得命令还没敲完就被判成半截帧丢掉。*/
    if ((s_rxState == RX_ASCII_ARG) || (s_rxState == RX_ASCII_TEXT) || (s_rxState == RX_ASCII_CAL))
    {
        timeout = ASCII_TIMEOUT_MS;
    }
    else
    {
        timeout = PARSE_TIMEOUT_MS;
    }

    if ((s_rxState != RX_HEAD0) && ((uint32_t)(now - s_lastRxMs) > timeout))
    {
        ParserReset();
    }
    s_lastRxMs = now;

    switch (s_rxState)
    {
        case RX_HEAD0:
            if (byte == FRAME_HEAD0)
            {
                s_rxState = RX_HEAD1;
                break;
            }

            /* ---- ASCII 快捷命令（空闲态才识别，不影响协议帧）----
             * L/R/B/D + 0/1 : 直接设置左转/右转/蜂鸣器/LED，省略数字 = 翻转
             * T + 文本      : OLED 显示并保存，回车/换行结束
             * S / C / P     : 保存 Flash / 清除 Flash / 重新读回
             * A             : 立即采集一次温度并上报
             * M             : 超声波测距一次（注意：不能用 U！ASCII 'U' = 0x55
             *                 与协议帧头 FRAME_HEAD0 同值，会被当帧头吃掉）
             */
            if ((byte == 'L') || (byte == 'R') || (byte == 'B') || (byte == 'D'))
            {
                s_asciiCmd = byte;
                s_rxState  = RX_ASCII_ARG;
            }
            else if (byte == 'T')
            {
                s_rxCount = 0;
                s_rxState = RX_ASCII_TEXT;
            }
            else if (byte == 'A')
            {
                DoSample();
            }
            else if (byte == 'S')
            {
                HandleStore(STORE_OP_SAVE);
            }
            else if (byte == 'C')
            {
                HandleStore(STORE_OP_CLEAR);
            }
            else if (byte == 'P')
            {
                HandleStore(STORE_OP_RELOAD);
            }
            else if (byte == 'K')
            {
                s_calRefC = 0u;                 /* 后面跟的数字才是参考温度 */
                s_rxState = RX_ASCII_CAL;
            }
            else if (byte == 'Z')
            {
                DoClearCal();                   /* 清除标定 */
            }
            else if (byte == 'M')
            {
                DoRadarOnce();                  /* 超声波测距一次(3取中值) */
            }
            else if (byte == 'O')
            {
                ToggleRadar();                  /* 倒车雷达连续测距 开/关（8Hz）*/
            }
            break;

        case RX_ASCII_CAL:
            if ((byte >= '0') && (byte <= '9'))
            {
                s_calRefC = (s_calRefC * 10u) + (uint32_t)(byte - '0');
                if (s_calRefC > 99u)
                {
                    s_calRefC = 99u;
                }
            }
            else
            {
                /* 回车/换行（或任何非数字字符）当作结束，按当前值标定 */
                DoCalibrate(s_calRefC);
                s_rxState = RX_HEAD0;
            }
            break;

        case RX_ASCII_ARG:
            if (byte == '1')
            {
                ExecuteControl(AsciiCodeOf(s_asciiCmd), 1u);
                s_rxState = RX_HEAD0;
            }
            else if (byte == '0')
            {
                ExecuteControl(AsciiCodeOf(s_asciiCmd), 0u);
                s_rxState = RX_HEAD0;
            }
            else
            {
                /* 后面不是数字：按"翻转一次"执行，再把当前字节重新喂回去 */
                ExecuteControl(AsciiCodeOf(s_asciiCmd),
                               (uint8_t)(!CurrentOf(AsciiCodeOf(s_asciiCmd))));
                s_rxState = RX_HEAD0;
                ParseByte(byte);
            }
            break;

        case RX_ASCII_TEXT:
            if ((byte == '\r') || (byte == '\n'))
            {
                if (s_rxCount > 0u)
                {
                    HandleText(s_rxData, s_rxCount);
                }
                s_rxState = RX_HEAD0;
            }
            else
            {
                s_rxData[s_rxCount] = byte;
                s_rxCount++;
                if (s_rxCount >= STORE_TEXT_MAX)
                {
                    HandleText(s_rxData, s_rxCount);    /* 满 32 字符直接显示 */
                    s_rxState = RX_HEAD0;
                }
            }
            break;

        case RX_HEAD1:
            if (byte == FRAME_HEAD1)
            {
                s_rxState = RX_LEN;
            }
            else if (byte == FRAME_HEAD0)
            {
                s_rxState = RX_HEAD1;       /* 连着来几个 0x55 也不断帧 */
            }
            else
            {
                ParserReset();
            }
            break;

        case RX_LEN:
            if (byte == 0u)
            {
                ParserReset();              /* 长度域至少得装下功能字本身 */
            }
            else
            {
                s_rxLen   = byte;
                s_rxState = RX_FUNC;
            }
            break;

        case RX_FUNC:
            s_rxFunc  = byte;
            s_rxCount = 0;

            /* 数据字节数统一由长度域给出：N = 功能字 + 数据 的字节数
             * （控制功能 N=3 → 数据 2 字节：控制单元 + 开关状态） */
            s_rxNeed = (uint8_t)((s_rxLen > 1u) ? (s_rxLen - 1u) : 0u);

            if (s_rxNeed == 0u)
            {
                DispatchFrame();
                ParserReset();
            }
            else if (s_rxNeed > FRAME_DATA_MAX)
            {
                SetMessage(CN_BAD_CODE);
                UpdateDisplay();
                ParserReset();
            }
            else
            {
                s_rxState = RX_DATA;
            }
            break;

        case RX_DATA:
            s_rxData[s_rxCount] = byte;
            s_rxCount++;
            s_rxNeed--;
            if (s_rxNeed == 0u)
            {
                DispatchFrame();
                ParserReset();
            }
            break;

        default:
            ParserReset();
            break;
    }
}

/* ========================= 超声波/红外（探测版新增） ========================= */

static void SendHex8(uint8_t v)
{
    static const char HEX[] = "0123456789ABCDEF";

    Usart_SendByte((uint8_t)HEX[v >> 4]);
    Usart_SendByte((uint8_t)HEX[v & 0x0Fu]);
}

static void SendU16(uint16_t v)
{
    char    num[6];
    uint8_t n = 0;

    if (v == 0u)
    {
        num[n] = '0';
        n++;
    }
    while (v > 0u)
    {
        num[n] = (char)('0' + (v % 10u));
        n++;
        v /= 10u;
    }
    while (n > 0u)
    {
        n--;
        Usart_SendByte((uint8_t)num[n]);
    }
}

/* 测一次距离（3 次取中值），串口打印 */
static void DoRadarOnce(void)
{
    uint16_t mm  = Hcsr04_GetDistanceMid3();
    uint16_t raw = Hcsr04_GetLastRawUs();
    uint8_t  err = Hcsr04_GetLastErr();

    if (mm == 0xFFFFu)
    {
        /* 失败分级：一眼看出卡在哪一步 */
        Usart_SendString("RADAR: timeout - ");
        if (err == HCSR04_ERR_NO_UP)
        {
            Usart_SendString("ECHO never went high (module no reply: check 5V / wiring / module)\r\n");
        }
        else if (err == HCSR04_ERR_STUCK_HIGH)
        {
            Usart_SendString("ECHO stuck high (TRIG-ECHO shorted? module stuck?)\r\n");
        }
        else if (err == HCSR04_ERR_SHORT)
        {
            Usart_SendString("pulse too short (<2cm / cross-talk)\r\n");
        }
        else if (err == HCSR04_ERR_RANGE)
        {
            Usart_SendString("echo pulse out of range (>4m)\r\n");
        }
        else
        {
            Usart_SendString("no echo\r\n");
        }
        Usart_SendString("RADAR: raw echo high = ");
        SendU16(raw);
        Usart_SendString(" us\r\n");
    }
    else
    {
        Usart_SendString("RADAR: ");
        SendU16(mm);
        Usart_SendString(" mm   (echo high ");
        SendU16(raw);
        Usart_SendString(" us)\r\n");
    }

    /* ECHO 当前电平：一直 0 = 模块没在拉高；一直 1 = 短路/卡死 */
    Usart_SendString("RADAR: ECHO pin level = ");
    Usart_SendString((Hcsr04_EchoLevel() != 0u) ? "1" : "0");
    Usart_SendString("   (send M again to re-measure)\r\n");
}

/* 主循环轮询：遥控器一帧码 -> 串口打印原始值（探测键值用） */
static void IrPoll(void)
{
    uint32_t raw;

    if (NecIr_GetRaw(&raw) != 0u)
    {
        uint8_t addr = (uint8_t)(raw >> 24);
        uint8_t ainv = (uint8_t)(raw >> 16);
        uint8_t cmd  = (uint8_t)(raw >> 8);
        uint8_t cinv = (uint8_t)(raw);

        Usart_SendString("IR: RAW=");
        SendHex8(addr);
        SendHex8(ainv);
        SendHex8(cmd);
        SendHex8(cinv);
        if (((uint8_t)~ainv == addr) && ((uint8_t)~cinv == cmd))
        {
            Usart_SendString("  ADDR=");
            SendHex8(addr);
            Usart_SendString(" CMD=");
            SendHex8(cmd);
            Usart_SendString("(");
            SendU16(cmd);
            Usart_SendString(") OK\r\n");
        }
        else
        {
            Usart_SendString("  (bad checksum)\r\n");
        }
    }
}

/* ========================= 倒车雷达服务 ========================= */

/* 蜂鸣器按分级打节奏。有源蜂鸣器只有“响/停”两态，近距的急促感
 * 靠缩短“停”的时间做出来，全程不阻塞主循环。*/
static void RadarBeepService(uint32_t now)
{
    uint16_t onMs  = s_zoneBeepOn[s_radarZone];
    uint16_t offMs = s_zoneBeepOff[s_radarZone];

    if ((s_radarOn == 0u) || (onMs == 0u))          /* 关雷达 / 安全距离：静音 */
    {
        if (s_radarBuzzing != 0u)
        {
            Beep_Off();
            s_radarBuzzing  = 0u;
            s_radarBeepTick = now;
        }
        return;
    }

    if (offMs == 0u)                                /* 危险档：长鸣，不用节奏 */
    {
        if (s_radarBuzzing == 0u)
        {
            Beep_On();
            s_radarBuzzing = 1u;
        }
        return;
    }

    if (s_radarBuzzing != 0u)
    {
        if ((uint32_t)(now - s_radarBeepTick) >= onMs)
        {
            Beep_Off();
            s_radarBuzzing  = 0u;
            s_radarBeepTick = now;
        }
    }
    else
    {
        if ((uint32_t)(now - s_radarBeepTick) >= offMs)
        {
            Beep_On();
            s_radarBuzzing  = 1u;
            s_radarBeepTick = now;
        }
    }
}

/* 主循环调用：连续测距 + 灯色分级 + 蜂鸣节奏 + 刷屏 + 节流上报 */
static void RadarService(void)
{
    uint32_t now;
    uint8_t  zone;

    if (s_radarOn == 0u)
    {
        return;
    }

    now = Get_SysRunTime();

    /* 1. 到点测一次（单次测距，无回波时约 60ms 超时，不长时间阻塞）*/
    if ((uint32_t)(now - s_radarTick) >= RADAR_PERIOD_MS)
    {
        s_radarTick = now;
        s_radarMm   = Hcsr04_GetDistanceMm();
        zone        = RadarZoneOf(s_radarMm);

        if (zone != s_radarZone)
        {
            s_radarZone     = zone;
            RGB_Set(s_zoneColor[zone]);             /* 绿 / 黄 / 黄 / 红 */
            s_radarBeepTick = now;
        }

        if (s_page == PAGE_RADAR)
        {
            UpdateDisplay();
        }
    }

    /* 2. 蜂鸣节奏每轮都跑，节奏才准 */
    RadarBeepService(now);

    /* 3. 串口节流上报（每 500ms 一行，免得刷屏把有用信息冲掉）*/
    if ((uint32_t)(now - s_radarLogTick) >= RADAR_LOG_MS)
    {
        s_radarLogTick = now;
        Usart_SendString("RADAR[ON] ");
        if (s_radarMm == 0xFFFFu)
        {
            Usart_SendString("-- ");
        }
        else
        {
            SendU16(s_radarMm);
        }
        Usart_SendString(" mm  ");
        Usart_SendString(RadarZoneMsg(s_radarZone));
        Usart_SendString("\r\n");
    }
}

/* 雷达模式开 / 关（串口发 O，或将来由遥控器按键映射）*/
static void ToggleRadar(void)
{
    if (s_radarOn != 0u)
    {
        s_radarOn      = 0u;
        s_radarZone    = RADAR_ZONE_NONE;
        s_radarMm      = 0xFFFFu;
        Beep_Off();
        s_radarBuzzing = 0u;
        s_page         = s_pageBak;                 /* 还原进雷达前的页 */
        ApplyHardware();                            /* 蜂鸣器/灯条交回串口控制 */
        SetMessage(CN_R_OFF);
        Usart_SendString("RADAR: off\r\n");
    }
    else
    {
        /* 灯条（PG0/1/2）和蜂鸣器要被雷达接管，先把抢这些资源的旧状态清掉 */
        if (Breath_IsActive() != 0u)
        {
            Breath_Stop();
            Usart_SendString("RADAR: breath lamp stopped (RGB lamp taken by radar)\r\n");
        }
        s_beepOn = 0u;
        s_ledOn  = 0u;

        s_radarOn       = 1u;
        s_pageBak       = s_page;
        s_page          = PAGE_RADAR;
        s_radarZone     = RADAR_ZONE_NONE;
        s_radarMm       = 0xFFFFu;
        s_radarTick     = Get_SysRunTime() - RADAR_PERIOD_MS;   /* 下一轮立刻测第一次 */
        s_radarLogTick  = Get_SysRunTime() - RADAR_LOG_MS;
        s_radarBeepTick = Get_SysRunTime();
        SetMessage(CN_R_ON);
        Usart_SendString("RADAR: on - continuous measure, send O again to stop\r\n");
    }

    UpdateDisplay();
    ReportState();
}

/* ========================= 按键处理 ========================= */

static void HandleKey(KeyEvent ev)
{
    uint8_t nextPage;

    switch (ev)
    {
        case KEY_EVT_KEY1_CLICK:        /* 循环切换：温度页 -> 文本页 -> 雷达页 */
            nextPage = (uint8_t)((s_page + 1u) % PAGE_COUNT);

            if (nextPage == PAGE_RADAR)
            {
                /* 切进雷达页顺便把雷达开起来，按键就能直接试；
                   已在雷达页则重复按就是重新刷一遍，不影响测距 */
                if (s_radarOn == 0u)
                {
                    ToggleRadar();              /* 内部会把页切到雷达页 */
                    return;
                }
                s_page = PAGE_RADAR;
            }
            else
            {
                if (s_radarOn != 0u)
                {
                    ToggleRadar();              /* 离开雷达页 = 停雷达，蜂鸣器/灯条同时停 */
                }
                s_page = nextPage;
            }

            UpdateDisplay();
            if (s_page == PAGE_TEXT)
            {
                Usart_SendString("PAGE: text\r\n");
            }
            else if (s_page == PAGE_RADAR)
            {
                Usart_SendString("PAGE: radar\r\n");
            }
            else
            {
                Usart_SendString("PAGE: temp\r\n");
            }
            break;

        case KEY_EVT_KEY2_CLICK:        /* 左转向灯呼吸灯 开/关 */
            ToggleBreath();
            break;

        case KEY_EVT_KEY3_CLICK:        /* 立即采集一次 */
            DoSample();
            break;

        default:
            break;
    }
}

/* ========================= 主函数 ========================= */

int main(void)
{
    uint8_t       rxByte;
    uint8_t       oledAck;
    uint32_t      now;
    StoreRecord_t rec;
    char          num[16];

    LED_Init();
    RGB_Init();
    RGB2_Init();
    Beep_Init();
    SysTick_Init();
    OLED_Init();
    Usart_Init(USART_BAUD_DEFAULT);
    Adc_Init();
    Key_Init();
    Breath_Init();
    Hcsr04_Init();
    NecIr_Init();

    TextFillSpace();
    SetMessage(CN_BOOTING);
    UpdateDisplay();

    Usart_SendString("\r\n=== AdcTemp Full (115200-8-N-1) ===\r\n");
    Usart_SendString("\xD6\xD0\xCE\xC4 : \xB1\xBE\xB9\xA4\xB3\xCC = \xB4\xAE\xBF\xDA\xBF\xD8\xD6\xC6 + ADC \xC4\xDA\xB2\xBF\xCE\xC2\xB6\xC8\xB2\xC9\xBC\xAF\xA3\xA8" "chapter8\xA3\xA9" "\r\n");
    Usart_SendString("ADC  : ADC1 \xCD\xA8\xB5\xC0" "16 \xC4\xDA\xB2\xBF\xCE\xC2\xB6\xC8\xB4\xAB\xB8\xD0\xC6\xF7\xA3\xAC\xC3\xBF 2 \xC3\xEB\xB2\xC9\xBC\xAF\xD2\xBB\xB4\xCE" "\r\n");
    Usart_SendString("\xCE\xC2\xB6\xC8 : \xB6\xC1\xB5\xC4\xCA\xC7\xD0\xBE\xC6\xAC\xD7\xD4\xC9\xED\xCE\xC2\xB6\xC8\xA3\xA8\xBD\xE1\xCE\xC2\xA3\xA9\xA3\xAC\xB2\xBB\xCA\xC7\xCA\xD2\xCE\xC2" "\r\n");
    Usart_SendString("OLED : 0.86 \xB4\xE7 128x32\xA3\xAC\xC8\xED\xBC\xFE I2C1  PB6=SCL  PB7=SDA" "\r\n");
    Usart_SendString("\xB4\xE6\xB4\xA2 : \xC4\xDA\xB2\xBF Flash \xD7\xEE\xBA\xF3\xD2\xBB\xD2\xB3 0x0807F800" "\r\n");
    Usart_SendString("\xBF\xD8\xD6\xC6 : 55 FF 03 06 <00\xD7\xF3\xD7\xAA 01\xD3\xD2\xD7\xAA 02\xB7\xE4\xC3\xF9\xC6\xF7 03\xB5\xC6\xCC\xF5> <00\xB9\xD8 01\xBF\xAA>" "\r\n");
    Usart_SendString("\xCE\xC4\xB1\xBE : 55 FF <len> 07 <text>   len = 1 + \xD7\xD6\xB7\xFB\xB8\xF6\xCA\xFD" "\r\n");
    Usart_SendString("\xB4\xE6\xB4\xA2 : 55 FF 02 08 <00\xB1\xA3\xB4\xE6 01\xC7\xE5\xB3\xFD 02\xB6\xC1\xBB\xD8>" "\r\n");
    Usart_SendString("\xBF\xEC\xBD\xDD : L/R/B/D <1\xBB\xF2" "0> \xBF\xAA/\xB9\xD8   T<\xCE\xC4\xB1\xBE>   S\xB1\xA3\xB4\xE6  C\xC7\xE5\xB3\xFD  P\xB6\xC1\xBB\xD8   A\xC1\xA2\xBC\xB4\xB2\xC9\xD1\xF9" "\r\n");
    Usart_SendString("\xB1\xEA\xB6\xA8 : K<\xCA\xD2\xCE\xC2> \xBB\xD8\xB3\xB5 = \xB1\xEA\xB6\xA8     Z = \xC7\xE5\xB3\xFD\xB1\xEA\xB6\xA8" "\r\n");
    Usart_SendString("\xB0\xB4\xBC\xFC : KEY1 \xC7\xD0\xBB\xBB\xD2\xB3\xC3\xE6   KEY2 \xBA\xF4\xCE\xFC\xB5\xC6(\xD7\xF3\xD7\xAA\xB5\xC6)   KEY3 \xC1\xA2\xBC\xB4\xB2\xC9\xD1\xF9" "\r\n");
    Usart_SendString("Info : " CN_BOOT_OK "\r\n");       /* 中文提示（GBK 编码）*/
    Usart_SendString("RADAR : HC-SR04 on J1 (1=5V 2=TRIG PF11 3=ECHO PF12 4=GND)\r\n");
    Usart_SendString("RADAR : M = single shot   O = \xB5\xB9\xB3\xB5\xC0\xD7\xB4\xEF\xBF\xAA/\xB9\xD8 (\xB7\xE4\xC3\xF9\xC6\xF7\xB7\xD6\xBC\xB6 + \xB5\xC6\xCC\xF5\xC2\xCC\xBB\xC6\xBA\xEC)\r\n");
    Usart_SendString("IR    : press NEC remote, raw code prints here (HS0038B -> PG11)\r\n");

    /* 顺手把 OLED 的自检结果打出来：屏不亮时一眼看出是接线问题还是驱动问题 */
    oledAck = OLED_Probe();
    if (oledAck == 1u)
    {
        Usart_SendString("OLED : ack ok, slave addr 0x78, 128x32 SSD1306\r\n");
    }
    else if (oledAck == 2u)
    {
        Usart_SendString("OLED : ack ok, slave addr 0x7A (SA0 = high)\r\n");
    }
    else
    {
        Usart_SendString("OLED : NO ACK - check SCL=PB6 / SDA=PB7 / 3V3 / GND\r\n");
    }

    /* 进阶二：开机先看内部 Flash 里有没有上次存下的内容 */
    if (Store_Load(&rec) != 0)
    {
        ApplyRecord(&rec);
        s_saved        = rec;
        s_bootRestored = 1;
        SetMessage(CN_BOOT_FLASH);
        Usart_SendString("BOOT : restored from internal flash\r\n");
    }
    else
    {
        s_bootRestored = 0;
        SetMessage(CN_NO_FLASH);
        Usart_SendString("BOOT : internal flash empty, using default\r\n");
    }

    ReportState();

    /* 标定状态提示：标定值跟文本、设备状态一起存在 Flash 的最后一页里。
       如果烧录固件时勾了"Erase Full Chip"（整片擦除），这一页也会被擦掉，
       于是温度回到手册公式的原始结果（这颗片子会偏高几度）。
       开机明确说一句，省得看到温度不对再猜原因。*/
    if (Adc_GetCalOffsetX100() != 0)
    {
        Usart_SendString("CAL  : " CN_CAL_USE "  offset ");
        FormatFixed(num, Adc_GetCalOffsetX100(), 2);
        Usart_SendString(num);
        Usart_SendString(" C (restored from flash)\r\n");
    }
    else
    {
        Usart_SendString("CAL  : " CN_CAL_NONE " - raw formula value\r\n");
        Usart_SendString("CAL  : " CN_CAL_HINT "\r\n");
    }

    /* 先采样一次，开机就有数据 */
    Adc_SampleTemp(&s_sample);
    ReportSample();
    s_lastSampleMs = Get_SysRunTime();
    UpdateDisplay();

    while (1)
    {
        /* 1. 串口：收字节喂协议解析器 */
        while (Usart_ReadByte(&rxByte) != 0)
        {
            ParseByte(rxByte);
        }

        now = Get_SysRunTime();

        /* 2. 按键：每 10ms 扫一次 */
        if ((uint32_t)(now - s_lastKeyMs) >= KEY_SCAN_PERIOD_MS)
        {
            s_lastKeyMs = now;
            HandleKey(Key_Scan());
        }

        /* 3. 温度：每 2 秒采集一次，刷屏 + 串口上报 */
        if ((uint32_t)(now - s_lastSampleMs) >= SAMPLE_PERIOD_MS)
        {
            s_lastSampleMs = now;
            DoSample();
        }

        /* 4. 红外遥控：有新帧就打印原始码（探测键值用） */
        IrPoll();

        /* 5. 倒车雷达：连续测距 + 分级蜂鸣 + 灯色 + 刷屏 */
        RadarService();

        /* 6. 转向灯闪烁 + 呼吸灯调占空比 */
        TurnSignalService();
        Breath_Service();
    }
}

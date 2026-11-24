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
 *      温度数据页（默认页，每次采样后都会回到这一页）——按任务书规定的三行格式：
 *          +------------------+
 *          | ADCvalue:  1738  |  <- ADC 原始值 0~4095
 *          | Voltage:  1.390V |  <- 换算后的模拟量（VDDA 反推，3 位小数）
 *          | Temp:     35.9C  |  <- 芯片结温（1 位小数；读数无效显示 --.-）
 *          | L0 R0 B0 D0  CAL |  <- 设备状态（L左转 R右转 B蜂鸣器 D灯条）+ 尾部标记
 *          +------------------+
 *          标签定长、数值在固定 5 格内右对齐，位数变化时数字不会左右抖。
 *          第 4 行状态行是任务书之外加的（方便演示时看设备开关状态），不影响验收格式。
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
#include "w25q64_drv.h"
#include "cn_msg.h"

/* ========================= 协议字段 ========================= */

#define FRAME_HEAD0         0x55
#define FRAME_HEAD1         0xFF

#define FUNC_CTRL           0x06        /* 控制设备 */
#define FUNC_STORE_DATA     0x07        /* 数据存储（本任务：写内部 / 外部 FLASH）*/
#define FUNC_STORE          0x08        /* 状态存储操作 */
#define FUNC_TEXT           0x09        /* 下发文本（原 0x07，为数据存储让位）*/

/* ---- 数据存储（功能字 0x07）的控制单元 ---- */
#define DATA_UNIT_INTERNAL  0x01        /* 存到片内 FLASH */
#define DATA_UNIT_EXTERNAL  0x02        /* 存到片外 W25Q64 */
#define DATA_MAX_LEN        20u         /* 数据域最大 20 字节（任务书规定）*/

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

/* ========================= 数据存储记录 =========================
 * 内部 / 外部 FLASH 存的是同一种记录，按字节流排布（不用结构体，避开编译器
 * 对齐填充的坑）：
 *      [0]  0x46 'F'     魔数 0
 *      [1]  0x53 'S'     魔数 1
 *      [2]  数据长度      0 ~ 20
 *      [3..22]  数据     最多 20 字节，不足部分为 0xFF
 *      [23] 校验         前 23 字节的累加和（低 8 位）
 * 一共 24 字节，内部 FLASH 按半字（2 字节）编程正好 12 次。
 */
#define DATA_REC_SIZE       24u
#define DATA_REC_MAGIC0     0x46u
#define DATA_REC_MAGIC1     0x53u
#define DATA_REC_OFF_LEN    2u
#define DATA_REC_OFF_DATA   3u
#define DATA_REC_OFF_CHECK  (DATA_REC_OFF_DATA + DATA_MAX_LEN)      /* = 23 */

/* 内部 FLASH 的数据页：倒数第二页（2KB 一页），和存设备状态的最后一页
 * 0x0807F800 分开，各擦各的，互不影响。
 * 注意：Keil 下载范围要设成 -FL07F000 才能保护这两页不被整片擦掉。*/
#define DATA_PAGE_ADDR      0x0807F000u

/* 外部 W25Q64 里放记录的地址（扇区 0 起始）*/
#define DATA_EXT_ADDR       0x000000u

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
static char         s_msg[OLED_COL_MAX + 1];    /* OLED 第 4 行的状态/提示 */

static uint32_t     s_lastSampleMs = 0;         /* 上次采样时刻 */
static uint32_t     s_lastKeyMs    = 0;         /* 上次按键扫描时刻 */
static uint32_t     s_sampleCount  = 0;         /* 开机以来的采样次数 */
static AdcTempSample_t s_sample;                /* 最近一次采样结果 */

/* ---- 两片 FLASH 里存的数据（分别显示在 OLED 第 1 / 第 3 行）---- */
static uint8_t      s_inData[DATA_MAX_LEN];     /* 内部 FLASH 读出的数据 */
static uint8_t      s_inLen        = 0;
static uint8_t      s_inValid      = 0;         /* 1 = 读到了有效记录 */

static uint8_t      s_exData[DATA_MAX_LEN];     /* 外部 FLASH 读出的数据 */
static uint8_t      s_exLen        = 0;
static uint8_t      s_exValid      = 0;         /* 1 = 读到了有效记录 */

static uint8_t      s_extOk        = 0;         /* W25Q64 是否检测到（1=在）*/

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

    /* 屏上用 8x8 ASCII 字库，只覆盖 0x20~0x7E。这里统一把超出范围的字节
       过滤成 '.'：万一有人再把 GBK 中文串传进来，屏上只会是一串点，
       而不是 OLED_ShowChar 逐个替换出来的问号 —— 一眼能看出是"内容不对"，
       不会误判成屏坏了。 */
    while ((i < OLED_COL_MAX) && (text[i] != '\0'))
    {
        uint8_t c = (uint8_t)text[i];
        s_msg[i] = ((c >= 0x20u) && (c <= 0x7Eu)) ? (char)c : '.';
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

/* ==================== OLED 固定三行版式 ====================
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

/* ========================= 温度采集与上报 ========================= */

/* 串口上报格式（本任务 chapter9）：
 *     Current Temperature is XXXX
 * ADC 原始值 / 电压按任务书要求取消 —— 屏上同样只留 Temp，
 * 串口与屏显示的内容各自独立（屏上另有 FLASH 数据两行）。
 */
static void ReportSample(void)
{
    char num[16];

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
}

/* 采一次 -> 串口上报 -> 刷新当前页（不强制跳页，用户在看哪页就留在哪页）*/
static void DoSample(void)
{
    Adc_SampleTemp(&s_sample);
    s_sampleCount++;
    ReportSample();
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
        SetMessage("BREATH OFF");
        Usart_SendString("BREATH: off\r\n");
    }
    else
    {
        Breath_Start();
        SetMessage("BREATH ON");
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
            SetMessage("BAD CODE");
            Usart_SendString("ERROR: unknown control code\r\n");
            UpdateDisplay();
            return;
    }

    if (SaveCurrent() != 0)     /* 状态变了就写进 Flash，下次开机自动恢复 */
    {
        SetMessage("CTRL OK");
    }
    else
    {
        SetMessage("FLASH ERR");
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
        SetMessage(log);        /* 新版式没有文本页了，收到的文本直接回显在第 4 行 */
    }
    else
    {
        SetMessage("FLASH ERR");
    }

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
                SetMessage("SAVED");
                Usart_SendString("FLASH: saved\r\n");
            }
            else
            {
                SetMessage("FLASH ERR");
                Usart_SendString("FLASH: write failed\r\n");
            }
            break;

        case STORE_OP_CLEAR:
            Store_Clear();
            s_saved.magic = 0u;     /* 清掉缓存，让下一次保存一定会真正写 */
            SetMessage("CLEARED");
            Usart_SendString("FLASH: cleared\r\n");
            break;

        case STORE_OP_RELOAD:
            if (Store_Load(&rec) != 0)
            {
                ApplyRecord(&rec);
                s_saved = rec;
                SetMessage("READ FLASH");
                Usart_SendString("FLASH: reloaded\r\n");
            }
            else
            {
                SetMessage("NO FLASH DATA");
                Usart_SendString("FLASH: no valid record\r\n");
            }
            break;

        default:
            SetMessage("BAD CODE");
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
        SetMessage("CAL SKIP");
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
        SetMessage("CAL OK");
    }
    else
    {
        SetMessage("FLASH ERR");
    }

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
        SetMessage("CAL CLEAR");
    }
    else
    {
        SetMessage("FLASH ERR");
    }

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

/* ========================= FLASH 数据存储 =========================
 * 内部 FLASH 和外部 W25Q64 存的是同一种 24 字节记录，校验方式也一样，
 * 所以两边的打包/校验代码共用。
 */

/* 按记录格式打包：魔数 + 长度 + 数据(不足补 0xFF) + 累加和 */
static void DataRec_Build(uint8_t *rec, const uint8_t *data, uint8_t len)
{
    uint8_t i;
    uint8_t sum = 0u;

    rec[0]                 = DATA_REC_MAGIC0;
    rec[1]                 = DATA_REC_MAGIC1;
    rec[DATA_REC_OFF_LEN]  = len;

    for (i = 0u; i < DATA_MAX_LEN; i++)
    {
        rec[DATA_REC_OFF_DATA + i] = (i < len) ? data[i] : 0xFFu;
    }

    for (i = 0u; i < DATA_REC_OFF_CHECK; i++)
    {
        sum = (uint8_t)(sum + rec[i]);
    }
    rec[DATA_REC_OFF_CHECK] = sum;
}

/* 校验记录。通过返回数据长度（1~20），失败返回 0 */
static uint8_t DataRec_Check(const uint8_t *rec)
{
    uint8_t i;
    uint8_t sum = 0u;
    uint8_t len;

    if ((rec[0] != DATA_REC_MAGIC0) || (rec[1] != DATA_REC_MAGIC1))
    {
        return 0u;
    }

    len = rec[DATA_REC_OFF_LEN];
    if ((len == 0u) || (len > DATA_MAX_LEN))
    {
        return 0u;
    }

    for (i = 0u; i < DATA_REC_OFF_CHECK; i++)
    {
        sum = (uint8_t)(sum + rec[i]);
    }
    if (sum != rec[DATA_REC_OFF_CHECK])
    {
        return 0u;
    }

    return len;
}

/* 写内部 FLASH：解锁 -> 擦数据页 -> 按半字逐次编程 -> 上锁 */
static uint8_t Data_SaveInternal(const uint8_t *data, uint8_t len)
{
    uint8_t  rec[DATA_REC_SIZE];
    uint32_t addr = DATA_PAGE_ADDR;
    uint16_t i;
    uint16_t halfWord;

    DataRec_Build(rec, data, len);

    FLASH_Unlock();

    if (FLASH_ErasePage(DATA_PAGE_ADDR) != FLASH_COMPLETE)
    {
        FLASH_Lock();
        return 0u;
    }

    for (i = 0u; i < DATA_REC_SIZE; i += 2u)
    {
        halfWord = (uint16_t)((uint16_t)rec[i] | ((uint16_t)rec[i + 1u] << 8));
        if (FLASH_ProgramHalfWord(addr, halfWord) != FLASH_COMPLETE)
        {
            FLASH_Lock();
            return 0u;
        }
        addr += 2u;
    }

    FLASH_Lock();

    return 1u;
}

/* 读内部 FLASH 记录，校验通过则把数据拷进 out */
static uint8_t Data_LoadInternal(uint8_t *out, uint8_t *outLen)
{
    const uint8_t *rec = (const uint8_t *)DATA_PAGE_ADDR;
    uint8_t len;
    uint8_t i;

    len = DataRec_Check(rec);
    if (len == 0u)
    {
        return 0u;
    }

    for (i = 0u; i < len; i++)
    {
        out[i] = rec[DATA_REC_OFF_DATA + i];
    }
    *outLen = len;

    return 1u;
}

/* 写外部 FLASH（W25Q64）：擦扇区 + 逐页写 */
static uint8_t Data_SaveExternal(const uint8_t *data, uint8_t len)
{
    uint8_t rec[DATA_REC_SIZE];

    if (s_extOk == 0u)
    {
        return 0u;
    }

    DataRec_Build(rec, data, len);

    return W25Q64_WriteData(DATA_EXT_ADDR, rec, (uint16_t)DATA_REC_SIZE);
}

/* 读外部 FLASH 记录 */
static uint8_t Data_LoadExternal(uint8_t *out, uint8_t *outLen)
{
    uint8_t rec[DATA_REC_SIZE];
    uint8_t len;
    uint8_t i;

    if (s_extOk == 0u)
    {
        return 0u;
    }

    W25Q64_Read(DATA_EXT_ADDR, rec, (uint16_t)DATA_REC_SIZE);
    len = DataRec_Check(rec);
    if (len == 0u)
    {
        return 0u;
    }

    for (i = 0u; i < len; i++)
    {
        out[i] = rec[DATA_REC_OFF_DATA + i];
    }
    *outLen = len;

    return 1u;
}

/* 重新读内部 FLASH 并刷新全局缓存。返回 1 = 有有效数据 */
static uint8_t RefreshInternal(void)
{
    s_inLen   = 0u;
    s_inValid = Data_LoadInternal(s_inData, &s_inLen);

    return s_inValid;
}

/* 重新读外部 FLASH 并刷新全局缓存。返回 1 = 有有效数据 */
static uint8_t RefreshExternal(void)
{
    s_exLen   = 0u;
    s_exValid = Data_LoadExternal(s_exData, &s_exLen);

    return s_exValid;
}

/* 串口按十六进制打印一段数据 */
static void ReportDataHex(const uint8_t *data, uint8_t len)
{
    static const char hex[] = "0123456789ABCDEF";
    char    buf[3];
    uint8_t i;

    if ((data == 0) || (len == 0u))
    {
        Usart_SendString("(empty)\r\n");
        return;
    }

    buf[2] = '\0';
    for (i = 0u; i < len; i++)
    {
        buf[0] = hex[(data[i] >> 4) & 0x0Fu];
        buf[1] = hex[data[i] & 0x0Fu];
        Usart_SendString(buf);
        if ((i + 1u) < len)
        {
            Usart_SendString(" ");
        }
    }
    Usart_SendString("\r\n");
}

/* 功能字 0x07（数据存储）：s_rxData = [控制单元][数据...]
 *   控制单元 0x01 -> 写内部 FLASH
 *   控制单元 0x02 -> 写外部 FLASH（W25Q64）*/
static void HandleStoreData(const uint8_t *data, uint8_t len)
{
    uint8_t unit;
    uint8_t dlen;

    if (len < 1u)
    {
        SetMessage("NO UNIT");
        Usart_SendString("ERROR: missing control unit\r\n");
        UpdateDisplay();
        return;
    }

    unit = data[0];
    dlen = (uint8_t)(len - 1u);

    if ((dlen == 0u) || (dlen > DATA_MAX_LEN))
    {
        SetMessage("BAD LEN");
        Usart_SendString("ERROR: data length must be 1~20\r\n");
        UpdateDisplay();
        return;
    }

    if (unit == DATA_UNIT_INTERNAL)
    {
        if (Data_SaveInternal(&data[1], dlen) != 0u)
        {
            (void)RefreshInternal();
            SetMessage("IN SAVED");
            Usart_SendString("STORE: internal flash saved -> ");
            ReportDataHex(s_inData, s_inLen);
        }
        else
        {
            SetMessage("IN FAIL");
            Usart_SendString("STORE: internal flash write failed\r\n");
        }
    }
    else if (unit == DATA_UNIT_EXTERNAL)
    {
        if (s_extOk == 0u)
        {
            SetMessage("NO W25Q64");
            Usart_SendString("STORE: W25Q64 not found\r\n");
            UpdateDisplay();
            return;
        }
        if (Data_SaveExternal(&data[1], dlen) != 0u)
        {
            (void)RefreshExternal();
            SetMessage("EX SAVED");
            Usart_SendString("STORE: external flash saved -> ");
            ReportDataHex(s_exData, s_exLen);
        }
        else
        {
            SetMessage("EX FAIL");
            Usart_SendString("STORE: external flash write failed\r\n");
        }
    }
    else
    {
        SetMessage("BAD UNIT");
        Usart_SendString("ERROR: unknown unit (01=internal 02=external)\r\n");
    }

    UpdateDisplay();
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
                SetMessage("BAD CODE");
                Usart_SendString("ERROR: missing control unit\r\n");
                UpdateDisplay();
            }
            break;

        case FUNC_STORE_DATA:
            HandleStoreData(s_rxData, s_rxCount);
            break;

        case FUNC_TEXT:
            HandleText(s_rxData, s_rxCount);
            break;

        case FUNC_STORE:
            HandleStore(s_rxData[0]);
            break;

        default:
            SetMessage("BAD CODE");
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
             * K + 数字      : 按室温标定，回车结束
             * Z             : 清除标定
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
                SetMessage("BAD CODE");
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

/* ========================= 按键处理 ========================= */

static void HandleKey(KeyEvent ev)
{
    switch (ev)
    {
        case KEY_EVT_KEY1_CLICK:        /* 读内部 FLASH 的数据 -> OLED 第 1 行 */
            if (RefreshInternal() != 0)
            {
                SetMessage("IN OK");
                Usart_SendString("KEY1 : internal flash -> ");
                ReportDataHex(s_inData, s_inLen);
            }
            else
            {
                SetMessage("IN EMPTY");
                Usart_SendString("KEY1 : internal flash empty\r\n");
            }
            UpdateDisplay();
            break;

        case KEY_EVT_KEY2_CLICK:        /* 左转向灯呼吸灯 开/关 */
            ToggleBreath();
            break;

        case KEY_EVT_KEY3_CLICK:        /* 读外部 FLASH(W25Q64) 的数据 -> OLED 第 3 行 */
            if (s_extOk == 0u)
            {
                SetMessage("NO W25Q64");
                Usart_SendString("KEY3 : W25Q64 not found\r\n");
            }
            else if (RefreshExternal() != 0)
            {
                SetMessage("EX OK");
                Usart_SendString("KEY3 : external flash -> ");
                ReportDataHex(s_exData, s_exLen);
            }
            else
            {
                SetMessage("EX EMPTY");
                Usart_SendString("KEY3 : external flash empty\r\n");
            }
            UpdateDisplay();
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
    s_extOk = W25Q64_Init();        /* 片外 SPI Flash：读 JEDEC ID 判断芯片在不在 */

    TextFillSpace();
    SetMessage("BOOTING");
    UpdateDisplay();

    Usart_SendString("=== FlashRW Full (chapter9)   115200-8-N-1 ===\r\n");
    Usart_SendString("\xD6\xD0\xCE\xC4: \xB1\xBE\xB9\xA4\xB3\xCC = \xC4\xDA\xB2\xBF" "FLASH + \xCD\xE2\xB2\xBFW25Q64 \xB6\xC1\xD0\xB4\xA3\xA8" "chapter9\xA3\xA9\r\n");
    Usart_SendString("\xCE\xC2\xB6\xC8: ADC1 \xCD\xA8\xB5\xC0" "16 \xC6\xAC\xC4\xDA\xCE\xC2\xB6\xC8\xB4\xAB\xB8\xD0\xC6\xF7\xA3\xAC\xC3\xBF 2 \xC3\xEB\xB2\xC9\xBC\xAF\xD2\xBB\xB4\xCE\xA3\xBB\xB4\xAE\xBF\xDA\xD6\xBB\xB1\xA8\xCE\xC2\xB6\xC8\r\n");
    Usart_SendString("OLED: 0.86 \xB4\xE7 128x32\xA3\xAC\xC8\xED\xBC\xFE I2C1  PB6=SCL  PB7=SDA\r\n");
    Usart_SendString("      \xB5\xDA" "1\xD0\xD0=\xC4\xDA\xB2\xBF" "FLASH\xCA\xFD\xBE\xDD  \xB5\xDA" "2\xD0\xD0=\xCE\xC2\xB6\xC8Temp  \xB5\xDA" "3\xD0\xD0=\xCD\xE2\xB2\xBF" "FLASH\xCA\xFD\xBE\xDD  \xB5\xDA" "4\xD0\xD0=\xD7\xB4\xCC\xAC\r\n");
    Usart_SendString("FLASH: \xC4\xDA\xB2\xBF 0x0807F000(\xCA\xFD\xBE\xDD\xD2\xB3) / 0x0807F800(\xD7\xB4\xCC\xAC\xD2\xB3)\r\n");
    Usart_SendString("       \xCD\xE2\xB2\xBF W25Q64 8MB @SPI2  PB12=CS PB13=SCK PB14=MISO PB15=MOSI\r\n");
    Usart_SendString("\xB4\xE6\xB4\xA2: 55 FF <len> 07 <01\xC4\xDA\xB2\xBF 02\xCD\xE2\xB2\xBF> <\xCA\xFD\xBE\xDD> <\xD2\xEC\xBB\xF2>    len = 1+1+N\xA3\xACN\xD7\xEE\xB4\xF3" "20\r\n");
    Usart_SendString("      \xC0\xFD: 55 FF 07 07 01 01 02 03 04 05 <\xD2\xEC\xBB\xF2>  -> 01 02 03 04 05 \xB4\xE6\xC4\xDA\xB2\xBF\r\n");
    Usart_SendString("\xBF\xD8\xD6\xC6: 55 FF 03 06 <00\xD7\xF3\xD7\xAA 01\xD3\xD2\xD7\xAA 02\xB7\xE4\xC3\xF9\xC6\xF7 03\xB5\xC6\xCC\xF5> <00\xB9\xD8 01\xBF\xAA>\r\n");
    Usart_SendString("\xCE\xC4\xB1\xBE: 55 FF <len> 09 <\xCE\xC4\xB1\xBE>    len = 1 + \xD7\xD6\xB7\xFB\xCA\xFD\r\n");
    Usart_SendString("\xD7\xB4\xCC\xAC: 55 FF 02 08 <00\xB1\xA3\xB4\xE6 01\xC7\xE5\xB3\xFD 02\xB6\xC1\xBB\xD8>\r\n");
    Usart_SendString("\xBF\xEC\xBD\xDD: L/R/B/D <1\xBB\xF2" "0> \xBF\xAA/\xB9\xD8   T<\xCE\xC4\xB1\xBE>   S\xB1\xA3\xB4\xE6 C\xC7\xE5\xB3\xFD P\xB6\xC1\xBB\xD8   A\xC1\xA2\xBC\xB4\xB2\xC9\xD1\xF9\r\n");
    Usart_SendString("\xB1\xEA\xB6\xA8: K<\xCA\xD2\xCE\xC2> \xBB\xD8\xB3\xB5 = \xB1\xEA\xB6\xA8     Z = \xC7\xE5\xB3\xFD\xB1\xEA\xB6\xA8\r\n");
    Usart_SendString("\xB0\xB4\xBC\xFC: KEY1 \xB6\xC1\xC4\xDA\xB2\xBF" "FLASH   KEY2 \xBA\xF4\xCE\xFC\xB5\xC6(\xD7\xF3\xD7\xAA\xB5\xC6)   KEY3 \xB6\xC1\xCD\xE2\xB2\xBF" "FLASH\r\n");
    Usart_SendString("Info : " CN_BOOT_OK "\r\n");

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

    /* 片外 W25Q64 自检结果 */
    if (s_extOk != 0u)
    {
        Usart_SendString("W25Q64: found, JEDEC ID = EF 40 17 (8MB)\r\n");
    }
    else
    {
        Usart_SendString("W25Q64: NOT FOUND - check SPI2 (PB12/13/14/15) or chip mounted\r\n");
    }

    /* 开机把两片 FLASH 里已有的数据读出来：屏上第 1 / 第 3 行立刻就有内容 */
    if (RefreshInternal() != 0)
    {
        Usart_SendString("BOOT : internal flash data -> ");
        ReportDataHex(s_inData, s_inLen);
    }
    else
    {
        Usart_SendString("BOOT : internal flash data empty\r\n");
    }

    if (s_extOk != 0u)
    {
        if (RefreshExternal() != 0)
        {
            Usart_SendString("BOOT : external flash data -> ");
            ReportDataHex(s_exData, s_exLen);
        }
        else
        {
            Usart_SendString("BOOT : external flash data empty\r\n");
        }
    }

    /* 再看内部 Flash 里有没有上次存下的设备状态 */
    if (Store_Load(&rec) != 0)
    {
        ApplyRecord(&rec);
        s_saved = rec;
        Usart_SendString("BOOT : restored device state from internal flash\r\n");
    }
    else
    {
        Usart_SendString("BOOT : internal flash state empty, using default\r\n");
    }

    ReportState();

    /* 第 4 行状态栏优先显示 W25Q64 在不在 —— 这颗芯片有没有焊，是这台板子上
       最要紧的一条信息，先摆在明面上 */
    SetMessage((s_extOk != 0u) ? "W25Q64 OK" : "NO W25Q64");

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
    s_sampleCount++;
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

        /* 4. 转向灯闪烁 + 呼吸灯调占空比 */
        TurnSignalService();
        Breath_Service();
    }
}

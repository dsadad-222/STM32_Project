/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   ADC 内部温度采集 + 串口控制 + OLED 显示 + 呼吸灯（chapter8 综合）
  *
  *          【本任务（chapter8）新增】
  *          1. 内部温度传感器采集：ADC1 的通道 16，每 2 秒采一次；
  *             温度(℃) = {(V25 - Vsense) / Avg_Slope} + 25
  *             V25 = 1.43V，Avg_Slope = 4.3mV/℃
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
  *  一、OLED 有两个显示页（4 行 x 16 字符）
  *      温度数据页（默认页，每次采样后都会回到这一页）：
  *          ADCvalue: 2018        <- ADC 原始值 0~4095
  *          Voltage :1.626        <- 换算后的模拟量（V）
  *          Temp    :30.52        <- 温度（℃），超量程时显示 --.--
  *          L0 R0 B0 D0           <- 设备状态（L 左转 R 右转 B 蜂鸣器 D 灯条）
  *      文本页（串口下发文本后自动切过来，或按 KEY1 切换）：
  *          第 1、2 行 = 串口发来的 32 个字符，第 3 行 = 提示信息
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
#define TURN_BLINK_PERIOD   500         /* 转向灯闪烁半周期（ms）*/

/* ========================= 本任务参数 ========================= */

#define SAMPLE_PERIOD_MS    2000u       /* 温度采集周期：2 秒 */
#define VALUE_WIDTH         5u          /* 数值在屏上右对齐的宽度 */

#define PAGE_TEMP           0u          /* OLED 温度数据页 */
#define PAGE_TEXT           1u          /* OLED 文本页 */

/* ========================= 运行状态 ========================= */

static uint8_t      s_leftTurnOn   = 0;
static uint8_t      s_rightTurnOn  = 0;
static uint8_t      s_beepOn       = 0;
static uint8_t      s_ledOn        = 0;
static uint8_t      s_blinkPhase   = 0;
static uint32_t     s_blinkTick    = 0;

static char         s_text[STORE_TEXT_MAX];     /* 当前文本，定长 32，空格补齐 */
static uint32_t     s_textLen      = 0;         /* 有效字符个数 */
static char         s_msg[OLED_COL_MAX + 1];    /* OLED 文本页第 3 行的提示 */
static uint8_t      s_bootRestored = 0;         /* 本次开机是否从 Flash 恢复 */

static uint8_t      s_page         = PAGE_TEMP; /* 当前显示页 */
static uint32_t     s_lastSampleMs = 0;         /* 上次采样时刻 */
static uint32_t     s_lastKeyMs    = 0;         /* 上次按键扫描时刻 */
static AdcTempSample_t s_sample;                /* 最近一次采样结果 */

/* 协议解析状态机 */
typedef enum
{
    RX_HEAD0 = 0,       /* 等帧头 0x55（空闲态同时识别 ASCII 快捷命令）*/
    RX_HEAD1,           /* 等帧头 0xFF */
    RX_LEN,             /* 等数据域长度 */
    RX_FUNC,            /* 等功能字 */
    RX_DATA,            /* 收数据 */
    RX_ASCII_ARG,       /* 快捷命令：等 '0'/'1'（等不到就翻转一次）*/
    RX_ASCII_TEXT       /* 快捷命令：收文本，回车/换行或满 32 字符结束 */
} RxState_t;

static RxState_t    s_rxState    = RX_HEAD0;
static uint8_t      s_rxLen      = 0;           /* 长度域声明的值 */
static uint8_t      s_rxFunc     = 0;           /* 本次帧的功能字 */
static uint8_t      s_rxNeed     = 0;           /* 还差几个数据字节 */
static uint8_t      s_rxCount    = 0;           /* 已收数据字节数 */
static uint8_t      s_rxData[FRAME_DATA_MAX];
static uint32_t     s_lastRxMs   = 0;
static uint8_t      s_asciiCmd   = 0;           /* 快捷命令首字母 L/R/B/D */

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

    /* 尾部 5 格提示当前状态：呼吸灯 / 文本页 / 开机来源 */
    if (Breath_IsActive() != 0)
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

/* 把最近一次采样结果刷到第 1~3 行 */
static void BuildSampleLines(char *l0, char *l1, char *l2)
{
    uint8_t pos;

    pos = 0;
    AppendTextX(l0, &pos, "ADCvalue:");
    AppendValue(l0, &pos, (int32_t)s_sample.rawValue, 0);
    PadLine(l0, &pos);

    pos = 0;
    AppendTextX(l1, &pos, "Voltage :");
    AppendValue(l1, &pos, (int32_t)s_sample.voltageMv, 3);     /* mV -> V，3 位小数 */
    PadLine(l1, &pos);

    pos = 0;
    AppendTextX(l2, &pos, "Temp    :");
    if (s_sample.valid != 0u)
    {
        AppendValue(l2, &pos, s_sample.tempX100, 2);            /* ×100 -> 2 位小数 */
    }
    else
    {
        AppendTextX(l2, &pos, "  --.--");                       /* 超量程：屏上显示 -- */
    }
    PadLine(l2, &pos);
}

static void UpdateDisplay(void)
{
    char    line[OLED_COL_MAX + 1];
    char    line0[OLED_COL_MAX + 1];
    char    line1[OLED_COL_MAX + 1];
    char    line2[OLED_COL_MAX + 1];
    uint8_t i;

    if (s_page == PAGE_TEXT)
    {
        /* 文本页：第 1、2 行放 32 个字符（16 x 2），第 3 行放提示 */
        OLED_ClearLine(0);
        OLED_ClearLine(1);
        for (i = 0; i < OLED_COL_MAX; i++)
        {
            OLED_ShowChar(i, 0, s_text[i]);
            OLED_ShowChar(i, 1, s_text[OLED_COL_MAX + i]);
        }
        OLED_ClearLine(2);
        OLED_ShowString(0, 2, s_msg);
    }
    else
    {
        /* 温度数据页：ADC 原始值 / 模拟量 / 温度 */
        BuildSampleLines(line0, line1, line2);
        OLED_ClearLine(0);
        OLED_ClearLine(1);
        OLED_ClearLine(2);
        OLED_ShowString(0, 0, line0);
        OLED_ShowString(0, 1, line1);
        OLED_ShowString(0, 2, line2);
    }

    /* 第 4 行两页共用：设备状态 */
    BuildStatusLine(line);
    OLED_ClearLine(3);
    OLED_ShowString(0, 3, line);

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

    if (s_rightTurnOn != 0)
    {
        s_blinkPhase = 1;
        s_blinkTick  = now;
        LED_On(LED2);
    }
    else
    {
        LED_Off(LED2);
    }

    if (s_beepOn != 0)
    {
        Beep_On();
    }
    else
    {
        Beep_Off();
    }

    RGB_Set((s_ledOn != 0) ? RGB_ALL : RGB_NONE);
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
        if (phase != 0) { LED_On(LED2); } else { LED_Off(LED2); }
    }
    else
    {
        LED_Off(LED2);
    }
}

/* ========================= 呼吸灯 ========================= */

static void ToggleBreath(void)
{
    if (Breath_IsActive() != 0)
    {
        Breath_Stop();
        SetMessage("BREATH OFF");
        Usart_SendString("BREATH: off\r\n");
    }
    else
    {
        Breath_Start();
        SetMessage("BREATH ON");
        Usart_SendString("BREATH: on (left turn lamp, LED1 PG14)\r\n");
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

    rec->magic    = STORE_MAGIC;
    rec->flags    = flags;
    rec->textLen  = s_textLen;
    rec->checksum = 0u;
    rec->reserved = 0u;

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
            SetMessage("BAD CTRL CODE");
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
        SetMessage("FLASH WRITE ERR");
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
        SetMessage("TEXT SAVED");
    }
    else
    {
        SetMessage("FLASH WRITE ERR");
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
                SetMessage("SAVED TO FLASH");
                Usart_SendString("FLASH: saved\r\n");
            }
            else
            {
                SetMessage("FLASH WRITE ERR");
                Usart_SendString("FLASH: write failed\r\n");
            }
            break;

        case STORE_OP_CLEAR:
            Store_Clear();
            s_saved.magic = 0u;     /* 清掉缓存，让下一次保存一定会真正写 */
            SetMessage("FLASH CLEARED");
            Usart_SendString("FLASH: cleared\r\n");
            break;

        case STORE_OP_RELOAD:
            if (Store_Load(&rec) != 0)
            {
                ApplyRecord(&rec);
                s_saved = rec;
                SetMessage("RELOADED FLASH");
                Usart_SendString("FLASH: reloaded\r\n");
            }
            else
            {
                SetMessage("NO FLASH DATA");
                Usart_SendString("FLASH: no valid record\r\n");
            }
            break;

        default:
            SetMessage("BAD STORE CODE");
            Usart_SendString("ERROR: unknown store code\r\n");
            break;
    }

    ReportState();
    UpdateDisplay();
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
                SetMessage("BAD CTRL CODE");
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
            SetMessage("BAD FUNC CODE");
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

    /* 帧内字节间隔超时 -> 半截帧作废，重新找帧头 */
    if ((s_rxState != RX_HEAD0) && ((uint32_t)(now - s_lastRxMs) > PARSE_TIMEOUT_MS))
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
                SetMessage("FRAME TOO LONG");
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
        case KEY_EVT_KEY1_CLICK:        /* 切换显示页 */
            s_page = (s_page == PAGE_TEMP) ? PAGE_TEXT : PAGE_TEMP;
            UpdateDisplay();
            Usart_SendString((s_page == PAGE_TEXT) ? "PAGE: text\r\n" : "PAGE: temp\r\n");
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

    LED_Init();
    RGB_Init();
    Beep_Init();
    SysTick_Init();
    OLED_Init();
    Usart_Init(USART_BAUD_DEFAULT);
    Adc_Init();
    Key_Init();
    Breath_Init();

    TextFillSpace();
    SetMessage("BOOTING...");
    UpdateDisplay();

    Usart_SendString("\r\n=== AdcTemp Full (115200-8-N-1) ===\r\n");
    Usart_SendString("ADC  : ADC1 channel16 internal temp sensor, every 2s\r\n");
    Usart_SendString("OLED : 0.86 inch, I2C1 PB6=SCL PB7=SDA\r\n");
    Usart_SendString("FLASH: internal, page 0x0807F800\r\n");
    Usart_SendString("ctrl : 55 FF 03 06 <00 left|01 right|02 beep|03 led> <00 off|01 on>\r\n");
    Usart_SendString("text : 55 FF <len> 07 <text>       (len = 1 + char count)\r\n");
    Usart_SendString("store: 55 FF 02 08 <00 save|01 clear|02 reload>\r\n");
    Usart_SendString("fast : L/R/B/D <1|0>   T <text>   S/C/P   A=sample now\r\n");
    Usart_SendString("key  : KEY1 page  KEY2 breath(LEFT lamp)  KEY3 sample now\r\n");

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
        SetMessage("BOOT FROM FLASH");
        Usart_SendString("BOOT : restored from internal flash\r\n");
    }
    else
    {
        s_bootRestored = 0;
        SetMessage("NO FLASH DATA");
        Usart_SendString("BOOT : internal flash empty, using default\r\n");
    }

    ReportState();

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

        /* 4. 转向灯闪烁 + 呼吸灯调占空比 */
        TurnSignalService();
        Breath_Service();
    }
}

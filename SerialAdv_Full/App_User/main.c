/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   串口数据控制测试（进阶版）
  *          PC 串口助手 -> USART1(PA9/PA10, 115200-8-N-1) -> 解析协议帧 -> 控制设备
  *
  *          基础要求：串口发命令控制左转向灯、右转向灯、蜂鸣器、LED 灯
  *          进阶一  ：串口下发文本，实时显示到板载 0.86 寸 OLED（I2C1: PB6/PB7）
  *          进阶二  ：串口下发的内容写进内部 Flash，掉电不丢；
  *                    下次开机先读 Flash，把状态和文本一起恢复出来
  *
  *  一、协议帧格式
  *      ┌────────┬────────┬──────────────┬────────────┬──────────────────┐
  *      │ 帧头 0 │ 帧头 1 │  数据域长度  │   功能字   │       数据       │
  *      │  0x55  │  0xFF  │      N       │    见下    │      见下        │
  *      └────────┴────────┴──────────────┴────────────┴──────────────────┘
  *      N = 数据域长度 = 功能字 + 数据 的字节数。数据后面还可以再跟校验字节，
  *          解析器收满自己需要的参数就立刻执行，多出来的字节会被忽略；
  *          所以发不发校验字节都能正常执行。
  *
 *  二、功能字
 *      0x06  控制设备，数据 = 控制单元 + 开关状态（与课件协议表一致）
 *              控制单元：0x00 左转向灯 LED1(PG14)   0x01 右转向灯 LED2(PG15)
 *                        0x02 蜂鸣器   (PG12)       0x03 LED 灯 RGB 灯条(PG0/PG1/PG2)
 *              开关状态：0x00 关，0x01 开 —— 按命令设置，不是翻转；
 *              兼容旧格式：只带 1 个数据字节时按"翻转一次"处理。
 *              帧尾若跟异或校验字节会被自动忽略（不影响执行）。
 *              转向灯开着时以 500ms 为半周期闪烁。设备状态会一并存进 Flash。
 *      0x07  下发文本，数据 = ASCII 文本（最多 32 个字符）
 *            文本立刻显示到 OLED 并写入 Flash
 *      0x08  存储操作，数据 = 操作码（1 字节）
 *              0x00 立刻把当前状态与文本存进 Flash
 *              0x01 清除 Flash 记录
 *              0x02 重新从 Flash 读回来并恢复
 *
 *  三、可以直接在串口助手里照抄的例子（长度域 = 功能字 + 数据 的字节数）
 *      55 FF 03 06 00 01     左转向灯 开
 *      55 FF 03 06 00 00     左转向灯 关
 *      55 FF 03 06 01 01     右转向灯 开
 *      55 FF 03 06 02 01     蜂鸣器   开      （...02 00 即关）
 *      55 FF 03 06 03 01     LED 灯   开
 *      55 FF 03 06 02        蜂鸣器 开/关（旧格式：翻转一次，仍然有效）
 *      55 FF 06 07 HELLO     OLED 显示 "HELLO" 并写入 Flash（6 = 功能字 + 5 个字符）
 *      55 FF 12 07 HELLO STM32 WORLD    两行显示并写入 Flash（18 = 1 + 17）
 *      55 FF 02 08 02        从 Flash 重新读回并恢复
 *      55 FF 02 08 01        清除 Flash 记录
  ******************************************************************************
  */

#include "led_drv.h"
#include "beep_drv.h"
#include "systick_drv.h"
#include "usart_drv.h"
#include "oled_drv.h"
#include "flash_drv.h"

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

/* ========================= 运行状态 ========================= */

static uint8_t      s_leftTurnOn   = 0;
static uint8_t      s_rightTurnOn  = 0;
static uint8_t      s_beepOn       = 0;
static uint8_t      s_ledOn        = 0;
static uint8_t      s_blinkPhase   = 0;
static uint32_t     s_blinkTick    = 0;

static char         s_text[STORE_TEXT_MAX];     /* 当前文本，定长 32，空格补齐 */
static uint32_t     s_textLen      = 0;         /* 有效字符个数 */
static char         s_msg[OLED_COL_MAX + 1];    /* OLED 第 4 行的提示 */
static uint8_t      s_bootRestored = 0;         /* 本次开机是否从 Flash 恢复 */

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

/* ========================= 显示辅助 ========================= */

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

/* 把当前状态 + 文本整屏刷到 OLED 上 */
static void UpdateDisplay(void)
{
    char    line[OLED_COL_MAX + 1];
    uint8_t i;

    /* 第 1 行：开机来源 + 四个设备状态，正好 15 个字符 */
    line[0]  = (s_bootRestored != 0) ? 'R' : 'N';   /* RST = 来自 Flash，NEW = 全新 */
    line[1]  = (s_bootRestored != 0) ? 'S' : 'E';
    line[2]  = (s_bootRestored != 0) ? 'T' : 'W';
    line[3]  = ' ';
    line[4]  = 'L';
    line[5]  = (s_leftTurnOn  != 0) ? '1' : '0';
    line[6]  = ' ';
    line[7]  = 'R';
    line[8]  = (s_rightTurnOn != 0) ? '1' : '0';
    line[9]  = ' ';
    line[10] = 'B';
    line[11] = (s_beepOn      != 0) ? '1' : '0';
    line[12] = ' ';
    line[13] = 'D';
    line[14] = (s_ledOn       != 0) ? '1' : '0';
    line[15] = '\0';

    OLED_ClearLine(0);
    OLED_ShowString(0, 0, line);

    /* 第 2、3 行：串口下发的文本（32 个字符正好两行）*/
    OLED_ClearLine(1);
    OLED_ClearLine(2);
    for (i = 0; i < OLED_COL_MAX; i++)
    {
        OLED_ShowChar(i, 1, s_text[i]);
        OLED_ShowChar(i, 2, s_text[OLED_COL_MAX + i]);
    }

    /* 第 4 行：提示 */
    OLED_ClearLine(3);
    OLED_ShowString(0, 3, s_msg);

    OLED_Refresh();
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

/* 转向灯闪烁：只有处于"开"状态的灯参与闪烁 */
static void TurnSignalService(void)
{
    uint32_t now = Get_SysRunTime();
    uint8_t  phase;

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

    if (s_leftTurnOn != 0)
    {
        if (phase != 0) { LED_On(LED1); } else { LED_Off(LED1); }
    }
    else
    {
        LED_Off(LED1);
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

/* ========================= 主函数 ========================= */

int main(void)
{
    uint8_t       rxByte;
    StoreRecord_t rec;

    LED_Init();
    RGB_Init();
    Beep_Init();
    SysTick_Init();
    OLED_Init();
    Usart_Init(USART_BAUD_DEFAULT);

    TextFillSpace();
    SetMessage("BOOTING...");
    UpdateDisplay();

    Usart_SendString("\r\n=== SerialCtrl Advanced (115200-8-N-1) ===\r\n");
    Usart_SendString("OLED : 0.86 inch, I2C1 PB6=SCL PB7=SDA\r\n");
    Usart_SendString("FLASH: internal, page 0x0807F800\r\n");
    Usart_SendString("ctrl : 55 FF 03 06 <00 left|01 right|02 beep|03 led> <00 off|01 on>\r\n");
    Usart_SendString("       (1-byte legacy form toggles; extra checksum byte ignored)\r\n");
    Usart_SendString("fast : L/R/B/D <1|0>   B1=beep on  B0=off  B=toggle\r\n");
    Usart_SendString("       T <text>        show on OLED\r\n");
    Usart_SendString("       S / C / P       save / clear / reload flash\r\n");
    Usart_SendString("text : 55 FF <len> 07 <text>       (len = 1 + char count)\r\n");
    Usart_SendString("store: 55 FF 02 08 <00 save|01 clear|02 reload>\r\n");

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
    UpdateDisplay();

    while (1)
    {
        while (Usart_ReadByte(&rxByte) != 0)
        {
            ParseByte(rxByte);
        }
        TurnSignalService();
    }
}

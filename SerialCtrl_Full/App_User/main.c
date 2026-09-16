/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   串口数据控制测试
  *          PC 串口助手 -> USART1(PA9/PA10, 115200-8-N-1) -> 解析协议帧 -> 控制板载设备
  *
  *          自定义协议帧：
  *              0x55  0xFF  0x03  0x06  <控制单元>  [校验字节]
  *              |     |     |     |      |
  *              |     |     |     |      +-- 0x00 左转向灯 / 0x01 右转向灯
  *              |     |     |     |          0x02 蜂鸣器   / 0x03 LED 灯
  *              |     |     |     +--------- 功能字
  *              |     |     +--------------- 数据域长度（功能字 + 控制单元 + 校验）
  *              |     +--------------------- 帧头 1
  *              +--------------------------- 帧头 0
  *          帧尾校验字节可发可不发：
  *              发了就按长度域跳过；不发也不会丢帧（下一帧的 0x55 会被重新识别）。
  *          即 55 FF 03 06 00 和 55 FF 03 06 00 AA 都能正常执行。
  *
  *          控制单元语义：每收到一次命令 -> 对应设备"开 / 关"翻转一次
  *              0x00 左转向灯 LED1(PG14)：开启后 500ms 周期闪烁
  *              0x01 右转向灯 LED2(PG15)：开启后 500ms 周期闪烁
  *              0x02 蜂鸣器  (PG12)  ：开启后持续鸣叫
  *              0x03 LED 灯  RGB 灯条(PG0/PG1/PG2)：开启后 RGB 全亮
  *          每帧执行后回发一行状态字符串，方便在串口助手里核对
  ******************************************************************************
  */

#include "led_drv.h"
#include "beep_drv.h"
#include "systick_drv.h"
#include "usart_drv.h"

/* ---------------- 协议字段 ---------------- */
#define FRAME_HEAD0         0x55
#define FRAME_HEAD1         0xFF
#define FRAME_FUNC_CODE     0x06

#define CTRL_LEFT_TURN      0x00
#define CTRL_RIGHT_TURN     0x01
#define CTRL_BEEP           0x02
#define CTRL_LED            0x03

/* ---------------- 运行时参数 ---------------- */
#define TURN_BLINK_PERIOD   500     /* 转向灯闪烁半周期（ms） */
#define PARSE_TIMEOUT_MS    200     /* 帧内字节间隔超时，丢弃半截帧 */

/* ---------------- 解析状态 ---------------- */
typedef enum
{
    PARSE_IDLE = 0,     /* 等帧头 0x55 */
    PARSE_HEAD1,        /* 等帧头 0xFF */
    PARSE_LEN,          /* 等数据域长度 */
    PARSE_FUNC,         /* 等功能字 */
    PARSE_CTRL,         /* 等控制单元 */
    PARSE_TAIL          /* 跳过数据域里多出来的字节 */
} ParseState_t;

/* ---------------- 设备状态 ---------------- */
static uint8_t      s_leftTurnOn  = 0;
static uint8_t      s_rightTurnOn = 0;
static uint8_t      s_beepOn      = 0;
static uint8_t      s_ledOn       = 0;
static uint8_t      s_blinkPhase  = 0;
static uint32_t     s_blinkTick   = 0;

static ParseState_t s_parseState  = PARSE_IDLE;
static uint8_t      s_skipCount   = 0;
static uint32_t     s_lastRxMs    = 0;

/* ====================== 设备执行 ====================== */

/* 串口回发当前设备状态 */
static void ReportState(void)
{
    Usart_SendString("STATUS  LEFT_TURN=");
    Usart_SendString(s_leftTurnOn ? "ON" : "OFF");
    Usart_SendString("  RIGHT_TURN=");
    Usart_SendString(s_rightTurnOn ? "ON" : "OFF");
    Usart_SendString("  BEEP=");
    Usart_SendString(s_beepOn ? "ON" : "OFF");
    Usart_SendString("  LED=");
    Usart_SendString(s_ledOn ? "ON" : "OFF");
    Usart_SendString("\r\n");
}

static void ExecuteCommand(uint8_t ctrl)
{
    uint32_t now = Get_SysRunTime();

    switch (ctrl)
    {
        case CTRL_LEFT_TURN:
            s_leftTurnOn = (uint8_t)(!s_leftTurnOn);
            if (s_leftTurnOn)
            {
                s_blinkPhase = 1;           /* 立刻点亮，不等第一个闪烁周期 */
                s_blinkTick  = now;
                LED_On(LED1);
            }
            else
            {
                LED_Off(LED1);
            }
            break;

        case CTRL_RIGHT_TURN:
            s_rightTurnOn = (uint8_t)(!s_rightTurnOn);
            if (s_rightTurnOn)
            {
                s_blinkPhase = 1;
                s_blinkTick  = now;
                LED_On(LED2);
            }
            else
            {
                LED_Off(LED2);
            }
            break;

        case CTRL_BEEP:
            s_beepOn = (uint8_t)(!s_beepOn);
            if (s_beepOn)
            {
                Beep_On();
            }
            else
            {
                Beep_Off();
            }
            break;

        case CTRL_LED:
            s_ledOn = (uint8_t)(!s_ledOn);
            RGB_Set(s_ledOn ? RGB_ALL : RGB_NONE);
            break;

        default:
            Usart_SendString("ERROR  unknown control code\r\n");
            return;
    }

    ReportState();
}

/* 转向灯闪烁：500ms 一个半周期，只有"开"状态的灯参与闪烁 */
static void TurnSignalService(void)
{
    uint32_t now = Get_SysRunTime();
    uint8_t  phase;

    if (!s_leftTurnOn && !s_rightTurnOn)
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

    if (s_leftTurnOn)
    {
        if (phase) { LED_On(LED1); } else { LED_Off(LED1); }
    }
    else
    {
        LED_Off(LED1);
    }

    if (s_rightTurnOn)
    {
        if (phase) { LED_On(LED2); } else { LED_Off(LED2); }
    }
    else
    {
        LED_Off(LED2);
    }
}

/* ====================== 协议解析 ====================== */

static void ResetParser(void)
{
    s_parseState = PARSE_IDLE;
    s_skipCount  = 0;
}

/* 逐字节喂入解析状态机 */
static void ParseByte(uint8_t byte)
{
    uint32_t now = Get_SysRunTime();

    /* 半截帧超时 -> 作废重找帧头 */
    if ((s_parseState != PARSE_IDLE) && ((uint32_t)(now - s_lastRxMs) > PARSE_TIMEOUT_MS))
    {
        ResetParser();
    }
    s_lastRxMs = now;

    switch (s_parseState)
    {
        case PARSE_IDLE:
            if (byte == FRAME_HEAD0)
            {
                s_parseState = PARSE_HEAD1;
            }
            break;

        case PARSE_HEAD1:
            if (byte == FRAME_HEAD1)
            {
                s_parseState = PARSE_LEN;
            }
            else if (byte == FRAME_HEAD0)
            {
                s_parseState = PARSE_HEAD1;     /* 连续多个 0x55 时不断帧 */
            }
            else
            {
                ResetParser();
            }
            break;

        case PARSE_LEN:
            /* 长度域至少要装下"功能字 + 控制单元"两个字节 */
            if (byte >= 2)
            {
                s_skipCount  = (uint8_t)(byte - 2);     /* 多出来的字节（校验等）先记下 */
                s_parseState = PARSE_FUNC;
            }
            else
            {
                ResetParser();
            }
            break;

        case PARSE_FUNC:
            if (byte == FRAME_FUNC_CODE)
            {
                s_parseState = PARSE_CTRL;
            }
            else
            {
                ResetParser();
            }
            break;

        case PARSE_CTRL:
            ExecuteCommand(byte);
            if (s_skipCount > 0)
            {
                s_parseState = PARSE_TAIL;
            }
            else
            {
                ResetParser();
            }
            break;

        case PARSE_TAIL:
            s_skipCount--;
            if (s_skipCount == 0)
            {
                /* 校验字节收完。若这一字节本身就是 0x55，说明上位机没发校验，
                   它就是下一帧的帧头，直接接着往下解析，避免丢帧。 */
                if (byte == FRAME_HEAD0)
                {
                    s_parseState = PARSE_HEAD1;
                    s_skipCount  = 0;
                }
                else
                {
                    ResetParser();
                }
            }
            break;

        default:
            ResetParser();
            break;
    }
}

/* ====================== 主函数 ====================== */
int main(void)
{
    uint8_t rxByte;

    LED_Init();
    RGB_Init();
    Beep_Init();
    SysTick_Init();
    Usart_Init(USART_BAUD_DEFAULT);

    Usart_SendString("\r\n=== SerialCtrl ready (115200-8-N-1) ===\r\n");
    Usart_SendString("frame : 55 FF 03 06 <ctrl>\r\n");
    Usart_SendString("ctrl  : 00 left  01 right  02 beep  03 led\r\n");

    while (1)
    {
        while (Usart_ReadByte(&rxByte) != 0)
        {
            ParseByte(rxByte);
        }
        TurnSignalService();
    }
}

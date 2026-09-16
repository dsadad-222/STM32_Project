/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   串口数据控制测试（简洁命令版）
  *          串口 ASCII 命令控制左右转向灯 / 蜂鸣器，KEY2 呼吸灯
  *
  *          一、串口命令（115200-8-N-1，命令末尾不用回车，发一个字母再发一个数字）
  *              L1 / L0   左转向灯 开 / 关
  *              R1 / R0   右转向灯 开 / 关
  *              D1 / D0   蜂鸣器   开 / 关
  *              只发字母不发数字 = 该设备翻转一次（开变关、关变开）
  *              3 秒内没等到数字，字母作废，等下一条命令
  *
  *          二、呼吸灯（与 chapter8 相同）
  *              KEY2(PG4) 按下：左转向灯（PG14 小灯 + PG0/1/2 顶部大灯三色同亮）
  *              进入呼吸效果（TIM2 中断 + 软件 PWM，占空比 0~100 来回变化，
  *              一亮一暗 2 秒一个来回）
  *              呼吸灯运行期间左转灯由 TIM2 中断独占，串口的 L 命令会先退出
  *              呼吸模式再执行。
  *
  *          三、反馈
  *              每次命令执行后回发一行状态：
  *                  STATUS  LEFT_TURN=ON  RIGHT_TURN=OFF  BEEP=OFF  BREATH=OFF
  *              不认识的字母回发：ERROR: unknown cmd
  ******************************************************************************
  */

#include "led_drv.h"
#include "beep_drv.h"
#include "systick_drv.h"
#include "usart_drv.h"
#include "key_drv.h"
#include "pwm_drv.h"

/* ========================= 设备编号 ========================= */

#define DEV_LEFT_TURN       0x00
#define DEV_RIGHT_TURN      0x01
#define DEV_BEEP            0x02

#define TURN_BLINK_PERIOD   500         /* 转向灯闪烁半周期（ms）*/
#define ASCII_TIMEOUT_MS    3000        /* 字母后等数字的超时 */

/* ========================= 运行状态 ========================= */

static uint8_t      s_leftTurnOn  = 0;
static uint8_t      s_rightTurnOn = 0;
static uint8_t      s_beepOn      = 0;
static uint8_t      s_blinkPhase  = 0;
static uint32_t     s_blinkTick   = 0;

/* 命令解析：空闲 -> 收到 L/R/D -> 等数字 */
static uint8_t      s_cmdLetter  = 0;        /* 当前等数字的命令字母，0 = 空闲 */
static uint32_t     s_cmdTick    = 0;        /* 字母到达时刻 */

/* ========================= 设备控制 ========================= */

static void ReportState(void)
{
    Usart_SendString("STATUS  LEFT_TURN=");
    Usart_SendString((s_leftTurnOn  != 0) ? "ON" : "OFF");
    Usart_SendString("  RIGHT_TURN=");
    Usart_SendString((s_rightTurnOn != 0) ? "ON" : "OFF");
    Usart_SendString("  BEEP=");
    Usart_SendString((s_beepOn      != 0) ? "ON" : "OFF");
    Usart_SendString("  BREATH=");
    Usart_SendString((Breath_IsActive() != 0) ? "ON" : "OFF");
    Usart_SendString("\r\n");
}

/* 按设备编号 + 开关状态执行；返回 0 = 执行成功 */
static uint8_t ExecuteControl(uint8_t dev, uint8_t on)
{
    on = (on != 0u) ? 1u : 0u;

    switch (dev)
    {
        case DEV_LEFT_TURN:
            if (Breath_IsActive() != 0)
            {
                Breath_Stop();          /* 手动控灯先退出呼吸模式 */
            }
            s_leftTurnOn = on;
            if (on != 0) { s_blinkPhase = 1; s_blinkTick = Get_SysRunTime(); LED_On(LED1); }
            else         { LED_Off(LED1); }
            break;

        case DEV_RIGHT_TURN:
            s_rightTurnOn = on;
            if (on != 0) { s_blinkPhase = 1; s_blinkTick = Get_SysRunTime(); LED_On(LED2); }
            else         { LED_Off(LED2); }
            break;

        case DEV_BEEP:
            s_beepOn = on;
            if (on != 0) { Beep_On(); } else { Beep_Off(); }
            break;

        default:
            return 1;                   /* 未知设备 */
    }
    return 0;
}

/* ========================= 呼吸灯 ========================= */

static void ToggleBreath(void)
{
    if (Breath_IsActive() != 0)
    {
        Breath_Stop();
        Usart_SendString("BREATH: off\r\n");
    }
    else
    {
        Breath_Start();
        Usart_SendString("BREATH: on (left turn light breathes)\r\n");
    }
    ReportState();
}

/* ========================= 串口命令解析 ========================= */

/* 命令字母 -> 设备编号 */
static uint8_t DevOf(uint8_t letter)
{
    switch (letter)
    {
        case 'L': return DEV_LEFT_TURN;
        case 'R': return DEV_RIGHT_TURN;
        case 'D': return DEV_BEEP;
        default:  return 0xFFu;
    }
}

/* 逐字节喂入；两字节一条命令：字母（L/R/D）+ 数字（0/1）*/
static void ParseByte(uint8_t byte)
{
    uint32_t now = Get_SysRunTime();

    /* 字母后面 3 秒没等到数字 -> 字母作废 */
    if ((s_cmdLetter != 0u) && ((uint32_t)(now - s_cmdTick) > ASCII_TIMEOUT_MS))
    {
        s_cmdLetter = 0u;
    }

    if (s_cmdLetter == 0u)
    {
        /* 空闲态：等命令字母 */
        if ((byte == 'L') || (byte == 'R') || (byte == 'D'))
        {
            s_cmdLetter = byte;
            s_cmdTick   = now;
        }
        else
        {
            Usart_SendString("ERROR: unknown cmd\r\n");
        }
        return;
    }

    /* 已有字母，等数字 */
    if (byte == '1')
    {
        ExecuteControl(DevOf(s_cmdLetter), 1u);
    }
    else if (byte == '0')
    {
        ExecuteControl(DevOf(s_cmdLetter), 0u);
    }
    else
    {
        /* 后面不是数字：按"翻转一次"执行，再把当前字节重新喂回去 */
        ExecuteControl(DevOf(s_cmdLetter),
                       (uint8_t)(!((s_cmdLetter == 'L') ? s_leftTurnOn
                                 : (s_cmdLetter == 'R') ? s_rightTurnOn
                                 : s_beepOn)));
        s_cmdLetter = 0u;
        ParseByte(byte);
        return;
    }
    s_cmdLetter = 0u;
    ReportState();
}

/* ========================= 转向灯闪烁 ========================= */

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

    /* 呼吸模式下左转灯由 TIM2 中断独占，这里不碰它 */
    if (breath == 0u)
    {
        if (s_leftTurnOn != 0)
        {
            if (phase != 0) { LED_On(LED1);  } else { LED_Off(LED1); }
        }
        else
        {
            LED_Off(LED1);
        }
    }

    if (s_rightTurnOn != 0)
    {
        if (phase != 0) { LED_On(LED2);  } else { LED_Off(LED2); }
    }
    else
    {
        LED_Off(LED2);
    }
}

/* ========================= 按键处理 ========================= */

static void HandleKey(KeyEvent ev)
{
    switch (ev)
    {
        case KEY_EVT_KEY2_CLICK:        /* 呼吸灯 开/关 */
            ToggleBreath();
            break;

        default:                        /* KEY1/KEY3 本版本无功能 */
            break;
    }
}

/* ========================= 主函数 ========================= */

int main(void)
{
    uint8_t    rxByte;
    uint32_t   now;
    uint32_t   lastKeyMs = 0;

    LED_Init();
    RGB_Init();                     /* 顶部左/右 RGB 大灯：呼吸灯要用左边这颗 */
    Beep_Init();
    SysTick_Init();
    Usart_Init(USART_BAUD_DEFAULT);
    Key_Init();
    Breath_Init();

    Usart_SendString("\r\n=== Serial Ctrl Std (115200-8-N-1) ===\r\n");
    Usart_SendString("cmd : L1/L0 left  R1/R0 right  D1/D0 beep\r\n");
    Usart_SendString("      letter alone = toggle that device\r\n");
    Usart_SendString("key : KEY2 = breath on/off (left turn light)\r\n");
    Usart_SendString("Info : system ready\r\n");
    ReportState();

    while (1)
    {
        /* 1. 串口：收字节喂命令解析器 */
        while (Usart_ReadByte(&rxByte) != 0)
        {
            ParseByte(rxByte);
        }

        now = Get_SysRunTime();

        /* 2. 按键：每 10ms 扫一次，KEY2 触发呼吸灯 */
        if ((uint32_t)(now - lastKeyMs) >= KEY_SCAN_PERIOD_MS)
        {
            lastKeyMs = now;
            HandleKey(Key_Scan());
        }

        /* 3. 转向灯 500ms 闪烁 + 呼吸灯调占空比 */
        TurnSignalService();
        Breath_Service();
    }
}

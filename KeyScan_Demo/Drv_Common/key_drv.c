/**
  ******************************************************************************
  * @file    Drv_Common/key_drv.c
  * @brief   按键扫描驱动实现（状态机 + 消抖）
  ******************************************************************************
  */

#include "key_drv.h"
#include "systick_drv.h"

void Key_Init(Key_t* key, GPIO_TypeDef* port, uint16_t pin, uint8_t pressedLevel)
{
    GPIO_InitTypeDef GPIO_InitStruct;

    /* 先开端口时钟：避免调用顺序变化导致按键读不到电平 */
    if      (port == GPIOA) RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA, ENABLE);
    else if (port == GPIOB) RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOB, ENABLE);
    else if (port == GPIOC) RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOC, ENABLE);
    else if (port == GPIOD) RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOD, ENABLE);
    else if (port == GPIOE) RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOE, ENABLE);
    else if (port == GPIOF) RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOF, ENABLE);
    else if (port == GPIOG) RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    key->port          = port;
    key->pin           = pin;
    key->pressedLevel  = pressedLevel;
    key->rawLevel      = 1;        /* 默认未按下 */
    key->stableLevel   = 1;
    key->prevLevel     = 1;
    key->rawChangeMs   = 0;
    key->state         = KS_IDLE;
    key->pressStartMs  = 0;
    key->releaseMs     = 0;
    key->longHoldActive= 0;
    key->event         = KEY_EVT_NONE;

    GPIO_InitStruct.GPIO_Pin  = pin;
    GPIO_InitStruct.GPIO_Mode = GPIO_Mode_IPU;   /* 外部已上拉，内部也上拉，双保险 */
    GPIO_InitStruct.GPIO_Speed= GPIO_Speed_50MHz;
    GPIO_Init(port, &GPIO_InitStruct);
}

static uint8_t Key_ReadRaw(Key_t* key)
{
    uint8_t v = GPIO_ReadInputDataBit(key->port, key->pin);
    return (v == key->pressedLevel) ? 1 : 0;   /* 1=按下 */
}

void Key_Scan(Key_t* key)
{
    uint32_t now = Get_SysRunTime();
    uint8_t  pressed = Key_ReadRaw(key);

    /* 1. 消抖：raw 与 stable 不同，启动消抖定时 */
    if (pressed != key->rawLevel)
    {
        if (key->rawChangeMs == 0)
        {
            key->rawChangeMs = now;
        }
        else if (now - key->rawChangeMs >= KEY_DEBOUNCE_MS)
        {
            /* 消抖通过，更新 stable */
            key->stableLevel = pressed;
            key->rawLevel    = pressed;
            key->rawChangeMs = 0;
        }
    }
    else
    {
        key->rawChangeMs = 0;
    }

    /* 2. 边沿检测：stable 变化触发 */
    if (key->stableLevel != key->prevLevel)
    {
        uint8_t prev = key->prevLevel;
        key->prevLevel = key->stableLevel;

        if (key->stableLevel && !prev)
        {
            /* 下降沿：按下 */
            key->pressStartMs = now;
            if (key->state == KS_CLICK_PENDING)
            {
                /* 第二次按下 → 标记双击 */
                key->state = KS_DOUBLE_CLICK;
            }
            else
            {
                key->state = KS_DEBOUNCE_DOWN;
            }
        }
        /* 上升沿（释放）在状态机里处理 */
    }

    /* 3. 状态机 */
    switch (key->state)
    {
        case KS_IDLE:
            break;

        case KS_DEBOUNCE_DOWN:
            /* 进入此状态说明 stable=1 已经稳定 20ms，确认按下 */
            key->state = KS_PRESSED;
            break;

        case KS_PRESSED:
            /* 长按判定 */
            if (now - key->pressStartMs >= KEY_SHORT_LONG_MS)
            {
                key->state          = KS_LONG_HOLD;
                key->longHoldActive = 1;
                key->event          = KEY_EVT_LONG_HOLD_START;
                break;
            }
            /* 已松开 → 短按候选 */
            if (key->stableLevel == 0)
            {
                key->state     = KS_CLICK_PENDING;
                key->releaseMs = now;
            }
            break;

        case KS_CLICK_PENDING:
            /* 等待第二次点击（双击窗口） */
            if (now - key->releaseMs >= KEY_DOUBLE_CLICK_MS)
            {
                key->state = KS_IDLE;
                key->event = KEY_EVT_CLICK;
            }
            break;

        case KS_DOUBLE_CLICK:
            key->state = KS_IDLE;
            key->event = KEY_EVT_DOUBLE_CLICK;
            break;

        case KS_LONG_HOLD:
            if (key->stableLevel == 0)
            {
                key->state          = KS_IDLE;
                key->longHoldActive = 0;
                key->event          = KEY_EVT_LONG_HOLD_END;
            }
            break;

        default:
            key->state = KS_IDLE;
            break;
    }
}

KeyEvent Key_GetEvent(Key_t* key)
{
    KeyEvent e = key->event;
    key->event = KEY_EVT_NONE;
    return e;
}

uint8_t Key_IsLongHold(Key_t* key)
{
    return key->longHoldActive;
}

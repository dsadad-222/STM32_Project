/**
  ******************************************************************************
  * @file    Drv_Common/key_drv.c
  * @brief   板载按键驱动实现：GPIO 上拉输入 + 20ms 消抖 + 单击识别
  ******************************************************************************
  */

#include "key_drv.h"
#include "systick_drv.h"

typedef struct
{
    uint16_t pin;           /* 引脚 */
    uint8_t  lastRaw;       /* 上一次读到的原始电平（1 = 按下，0 = 松开）*/
    uint8_t  stable;        /* 消抖后的稳定电平 */
    uint32_t rawChangeMs;   /* 原始电平最后一次变化的时刻 */
} KeyState_t;

static KeyState_t s_keys[3] =
{
    { KEY1_PIN, 0u, 0u, 0u },       /* 上电时按键都是松开的 */
    { KEY2_PIN, 0u, 0u, 0u },
    { KEY3_PIN, 0u, 0u, 0u }
};

void Key_Init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(KEY_GPIO_CLK, ENABLE);

    /* 板上已有 10K 上拉，这里仍按上拉输入配置，双保险 */
    gpio.GPIO_Pin   = KEY1_PIN | KEY2_PIN | KEY3_PIN;
    gpio.GPIO_Mode  = GPIO_Mode_IPU;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(KEY_PORT, &gpio);
}

/* 读原始电平：返回 1 = 按下（低电平），0 = 松开（高电平）*/
static uint8_t KeyReadRaw(KeyState_t *key)
{
    return (uint8_t)((GPIO_ReadInputDataBit(KEY_PORT, key->pin) == Bit_RESET) ? 1u : 0u);
}

KeyEvent Key_Scan(void)
{
    uint32_t now = Get_SysRunTime();
    uint8_t  i;
    KeyEvent event = KEY_EVT_NONE;

    for (i = 0u; i < 3u; i++)
    {
        KeyState_t *key = &s_keys[i];
        uint8_t raw = KeyReadRaw(key);

        if (raw != key->lastRaw)
        {
            key->lastRaw     = raw;
            key->rawChangeMs = now;
        }

        if ((raw != key->stable) &&
            ((uint32_t)(now - key->rawChangeMs) >= KEY_DEBOUNCE_MS))
        {
            key->stable = raw;              /* 消抖通过，电平才算真正变化 */

            if ((key->stable == 1u) && (event == KEY_EVT_NONE))
            {
                /* 按下沿 -> 报一次单击事件（按下就响应，手感更快）*/
                if (i == 0u)      { event = KEY_EVT_KEY1_CLICK; }
                else if (i == 1u) { event = KEY_EVT_KEY2_CLICK; }
                else              { event = KEY_EVT_KEY3_CLICK; }
            }
        }
    }

    return event;
}

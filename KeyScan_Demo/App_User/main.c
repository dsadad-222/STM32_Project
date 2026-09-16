/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   单按键多动作控制 LED 测试
  *          KEY1(PG3) 单击 -> LED1(PG14) 长亮
  *          KEY1(PG3) 双击 -> LED2(PG15) 长亮
  *          KEY1(PG3) 长按 -> LED1+LED2 全关
  *
  *          时基：SysTick 1ms，按键扫描周期 10ms
  ******************************************************************************
  */

#include "led_drv.h"
#include "key_drv.h"
#include "systick_drv.h"

#define KEY1_PORT    GPIOG
#define KEY1_PIN     GPIO_Pin_3
#define KEY_SCAN_PERIOD_MS    10

static Key_t s_key1;

static void HandleKey1Event(KeyEvent evt)
{
    switch (evt)
    {
        case KEY_EVT_CLICK:         LED_On(LED1);    break;  /* 单击 -> LED1 长亮 */
        case KEY_EVT_DOUBLE_CLICK:  LED_On(LED2);    break;  /* 双击 -> LED2 长亮 */
        case KEY_EVT_LONG_HOLD_END: LED_Off(LED_ALL); break; /* 长按松开 -> 全关 */
        default: break;
    }
}

int main(void)
{
    uint32_t lastScanMs = 0;

    LED_Init();
    Key_Init(&s_key1, KEY1_PORT, KEY1_PIN, Bit_RESET);
    SysTick_Init();

    while (1)
    {
        uint32_t now = Get_SysRunTime();

        if (now - lastScanMs >= KEY_SCAN_PERIOD_MS)
        {
            lastScanMs = now;
            Key_Scan(&s_key1);
            KeyEvent evt = Key_GetEvent(&s_key1);
            if (evt != KEY_EVT_NONE)
            {
                HandleKey1Event(evt);
            }
        }
    }
}

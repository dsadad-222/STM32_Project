/**
  ******************************************************************************
  * @file    App_User/main.c
  * @author  陈相林 (智能3班)
  * @brief   综合任务：SysTick 编程 + 外部中断控制测试
  *          - SysTick 提供 1ms 时基，主循环每 1s 翻转 LED1
  *          - EXTI 下降沿中断：KEY1(PG3) 翻转 LED1，KEY2(PG4) 翻转 LED2，
  *            KEY3(PG5) 同时翻转 LED1 与 LED2
  ******************************************************************************
  */

#include "led_drv.h"
#include "exti_drv.h"
#include "systick_drv.h"

int main(void)
{
    uint64_t c_Time;

    LED_Init();
    EXTI_KeyInit();
    SysTick_Init();

    c_Time = Get_SysRunTime();
    LED_On(LED1); /* 上电先点亮 LED1 */

    while (1)
    {
        /* 每 1000ms 翻转 LED1，演示 SysTick 定时 */
        if (Get_SysRunTime() - c_Time > 1000)
        {
            c_Time = Get_SysRunTime();
            LED_Toggle(LED1);
        }
    }
}

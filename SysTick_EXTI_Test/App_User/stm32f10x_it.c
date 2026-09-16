/**
  ******************************************************************************
  * @file    App_User/stm32f10x_it.c
  * @author  陈相林 (智能3班)
  * @brief   中断服务函数：SysTick 1ms 计数 + EXTI3/4/9_5 按键中断
  ******************************************************************************
  */

#include "stm32f10x_it.h"
#include "led_drv.h"

extern volatile uint64_t g_sysRunTime;

void SysTick_Handler(void)
{
    g_sysRunTime++;
}

void EXTI3_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line3) != RESET)
    {
        LED_Toggle(LED1);
        EXTI_ClearITPendingBit(EXTI_Line3);
    }
}

void EXTI4_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line4) != RESET)
    {
        LED_Toggle(LED2);
        EXTI_ClearITPendingBit(EXTI_Line4);
    }
}

void EXTI9_5_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line5) != RESET)
    {
        LED_Toggle(LED1);
        LED_Toggle(LED2);
        EXTI_ClearITPendingBit(EXTI_Line5);
    }
}

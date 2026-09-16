/*
 * stm32f10x_it.c
 * SysTick + EXTI3/4/9_5 interrupt handlers
 */

#include "stm32f10x_it.h"
#include "led_drv.h"
#include "systick_drv.h"

void SysTick_Handler(void)
{
    sys_ms++;
}

void EXTI3_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line3) != RESET) {
        led_toggle(LED_1);
        EXTI_ClearITPendingBit(EXTI_Line3);
    }
}

void EXTI4_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line4) != RESET) {
        led_toggle(LED_2);
        EXTI_ClearITPendingBit(EXTI_Line4);
    }
}

void EXTI9_5_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line5) != RESET) {
        led_toggle(LED_BOTH);
        EXTI_ClearITPendingBit(EXTI_Line5);
    }
}

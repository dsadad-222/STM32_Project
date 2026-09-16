/*
 * exti_drv.c
 * EXTI key init: PG3/4/5 falling edge, EXTI3/4/9_5
 */

#include "exti_drv.h"
#include "stm32f10x.h"

void exti_key_init(void)
{
    GPIO_InitTypeDef gpio;
    EXTI_InitTypeDef exti;
    NVIC_InitTypeDef nvic;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG | RCC_APB2Periph_AFIO, ENABLE);

    gpio.GPIO_Pin  = GPIO_Pin_3 | GPIO_Pin_4 | GPIO_Pin_5;
    gpio.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOG, &gpio);

    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource3);
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource4);
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource5);

    exti.EXTI_Mode    = EXTI_Mode_Interrupt;
    exti.EXTI_Trigger = EXTI_Trigger_Falling;
    exti.EXTI_LineCmd = ENABLE;

    exti.EXTI_Line = EXTI_Line3;
    EXTI_Init(&exti);
    exti.EXTI_Line = EXTI_Line4;
    EXTI_Init(&exti);
    exti.EXTI_Line = EXTI_Line5;
    EXTI_Init(&exti);

    nvic.NVIC_IRQChannelPreemptionPriority = 2;
    nvic.NVIC_IRQChannelSubPriority        = 0;
    nvic.NVIC_IRQChannelCmd                = ENABLE;

    nvic.NVIC_IRQChannel = EXTI3_IRQn;
    NVIC_Init(&nvic);
    nvic.NVIC_IRQChannel = EXTI4_IRQn;
    NVIC_Init(&nvic);
    nvic.NVIC_IRQChannel = EXTI9_5_IRQn;
    NVIC_Init(&nvic);
}

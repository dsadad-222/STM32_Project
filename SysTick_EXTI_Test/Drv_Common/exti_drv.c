/**
  ******************************************************************************
  * @file    Drv_Common/exti_drv.c
  * @author  陈相林 (智能3班)
  * @brief   EXTI 按键初始化：PG3/4/5 下降沿触发，EXTI3/4/9_5
  ******************************************************************************
  */

#include "exti_drv.h"
#include "stm32f10x.h"

void EXTI_KeyInit(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    EXTI_InitTypeDef EXTI_InitStructure;
    NVIC_InitTypeDef NVIC_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG | RCC_APB2Periph_AFIO, ENABLE);

    /* KEY1/2/3 浮空输入 */
    GPIO_InitStructure.GPIO_Pin  = GPIO_Pin_3 | GPIO_Pin_4 | GPIO_Pin_5;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOG, &GPIO_InitStructure);

    /* 映射 EXTI 线 */
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource3);
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource4);
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource5);

    /* 通用配置：中断模式 + 下降沿触发 */
    EXTI_InitStructure.EXTI_Mode    = EXTI_Mode_Interrupt;
    EXTI_InitStructure.EXTI_Trigger = EXTI_Trigger_Falling;
    EXTI_InitStructure.EXTI_LineCmd = ENABLE;

    EXTI_InitStructure.EXTI_Line = EXTI_Line3;
    EXTI_Init(&EXTI_InitStructure);

    EXTI_InitStructure.EXTI_Line = EXTI_Line4;
    EXTI_Init(&EXTI_InitStructure);

    EXTI_InitStructure.EXTI_Line = EXTI_Line5;
    EXTI_Init(&EXTI_InitStructure);

    /* NVIC 配置 */
    NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 2;
    NVIC_InitStructure.NVIC_IRQChannelSubPriority         = 0;
    NVIC_InitStructure.NVIC_IRQChannelCmd                 = ENABLE;

    NVIC_InitStructure.NVIC_IRQChannel = EXTI3_IRQn;
    NVIC_Init(&NVIC_InitStructure);

    NVIC_InitStructure.NVIC_IRQChannel = EXTI4_IRQn;
    NVIC_Init(&NVIC_InitStructure);

    NVIC_InitStructure.NVIC_IRQChannel = EXTI9_5_IRQn;
    NVIC_Init(&NVIC_InitStructure);
}

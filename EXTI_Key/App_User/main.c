/**
  ******************************************************************************
  * @file    App_User/main.c
  * @author  陈相林 (智能3班)
  * @brief   标准库版：外部中断控制测试
  *          使用 STM32F10x 标准外设库 API 配置 EXTI：
  *          KEY1(PG3) 下降沿触发 -> 翻转 LED1(PG14)
  *          KEY2(PG4) 下降沿触发 -> 翻转 LED2(PG15)
  *          KEY3(PG5) 下降沿触发 -> 同时翻转 LED1、LED2
  ******************************************************************************
  */

#include "stm32f10x.h"

/* LED 引脚配置：PG14 / PG15 推挽输出 */
static void LED_GPIO_Config(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    GPIO_InitStructure.GPIO_Pin   = GPIO_Pin_14 | GPIO_Pin_15;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOG, &GPIO_InitStructure);

    GPIO_ResetBits(GPIOG, GPIO_Pin_14 | GPIO_Pin_15);
}

/* 按键引脚配置：PG3 / PG4 / PG5 上拉输入 */
static void KEY_GPIO_Config(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG | RCC_APB2Periph_AFIO, ENABLE);

    GPIO_InitStructure.GPIO_Pin  = GPIO_Pin_3 | GPIO_Pin_4 | GPIO_Pin_5;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOG, &GPIO_InitStructure);
}

/* EXTI 外部中断配置：PG3/4/5 -> EXTI3/4/5，下降沿触发 */
static void EXTI_GPIO_Config(void)
{
    EXTI_InitTypeDef EXTI_InitStructure;
    NVIC_InitTypeDef NVIC_InitStructure;

    /* 将 PG3/PG4/PG5 映射到 EXTI3/EXTI4/EXTI5 */
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource3);
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource4);
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource5);

    EXTI_InitStructure.EXTI_Line    = EXTI_Line3 | EXTI_Line4 | EXTI_Line5;
    EXTI_InitStructure.EXTI_Mode    = EXTI_Mode_Interrupt;
    EXTI_InitStructure.EXTI_Trigger = EXTI_Trigger_Falling;
    EXTI_InitStructure.EXTI_LineCmd = ENABLE;
    EXTI_Init(&EXTI_InitStructure);

    /* 配置并使能 NVIC 中断通道 */
    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_1);

    NVIC_InitStructure.NVIC_IRQChannel                   = EXTI3_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 1;
    NVIC_InitStructure.NVIC_IRQChannelSubPriority        = 0;
    NVIC_InitStructure.NVIC_IRQChannelCmd                = ENABLE;
    NVIC_Init(&NVIC_InitStructure);

    NVIC_InitStructure.NVIC_IRQChannel                   = EXTI4_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 1;
    NVIC_InitStructure.NVIC_IRQChannelSubPriority        = 1;
    NVIC_Init(&NVIC_InitStructure);

    NVIC_InitStructure.NVIC_IRQChannel                   = EXTI9_5_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 1;
    NVIC_InitStructure.NVIC_IRQChannelSubPriority        = 2;
    NVIC_Init(&NVIC_InitStructure);
}

/* KEY1 中断服务函数：翻转 LED1 */
void EXTI3_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line3) != RESET) {
        GPIO_WriteBit(GPIOG, GPIO_Pin_14,
                      (BitAction)(1 - GPIO_ReadOutputDataBit(GPIOG, GPIO_Pin_14)));
        EXTI_ClearITPendingBit(EXTI_Line3);
    }
}

/* KEY2 中断服务函数：翻转 LED2 */
void EXTI4_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line4) != RESET) {
        GPIO_WriteBit(GPIOG, GPIO_Pin_15,
                      (BitAction)(1 - GPIO_ReadOutputDataBit(GPIOG, GPIO_Pin_15)));
        EXTI_ClearITPendingBit(EXTI_Line4);
    }
}

/* KEY3 中断服务函数（EXTI9_5 共享通道）：同时翻转 LED1、LED2 */
void EXTI9_5_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line5) != RESET) {
        GPIO_WriteBit(GPIOG, GPIO_Pin_14,
                      (BitAction)(1 - GPIO_ReadOutputDataBit(GPIOG, GPIO_Pin_14)));
        GPIO_WriteBit(GPIOG, GPIO_Pin_15,
                      (BitAction)(1 - GPIO_ReadOutputDataBit(GPIOG, GPIO_Pin_15)));
        EXTI_ClearITPendingBit(EXTI_Line5);
    }
}

int main(void)
{
    LED_GPIO_Config();
    KEY_GPIO_Config();
    EXTI_GPIO_Config();

    while (1)
    {
        /* 中断中完成按键控制，主循环空转 */
    }
}

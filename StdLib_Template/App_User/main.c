/**
  ******************************************************************************
  * @file    App_User/main.c
  * @author  陈相林 (智能3班)
  * @brief   标准库版：GPIO 控制 LED 闪烁（对应任务2）
  *          使用 STM32F10x 标准外设库 API，而非寄存器直写
  ******************************************************************************
  */

#include "stm32f10x.h"

/* 简易软件延时 */
static void Delay(__IO uint32_t nCount)
{
    for (; nCount != 0; nCount--);
}

/* LED 引脚配置：PG14 / PG15 推挽输出 */
static void LED_GPIO_Config(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    /* 1. 开启 GPIOG 外设时钟（标准库必须显式开时钟） */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    /* 2. 配置引脚为推挽输出、50MHz */
    GPIO_InitStructure.GPIO_Pin  = GPIO_Pin_14 | GPIO_Pin_15;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOG, &GPIO_InitStructure);
}

int main(void)
{
    /* 系统时钟由 startup 调用的 SystemInit() 配置为 72MHz */
    LED_GPIO_Config();

    while (1)
    {
        /* 置位 -> 灯亮 */
        GPIO_SetBits(GPIOG, GPIO_Pin_14);
        Delay(0x3FFFFF);

        /* 复位 -> 灯灭 */
        GPIO_ResetBits(GPIOG, GPIO_Pin_14);
        Delay(0x3FFFFF);
    }
}

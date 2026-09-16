/**
  ******************************************************************************
  * @file    Drv_Common/led_drv.c
  * @author  陈相林 (智能3班)
  * @brief   LED 驱动实现：PG14 / PG15，高电平点亮
  ******************************************************************************
  */

#include "led_drv.h"

#define LED1_PIN    GPIO_Pin_14
#define LED2_PIN    GPIO_Pin_15
#define LED_PORT    GPIOG

static uint16_t LED_PinGet(LED_TypeDef led)
{
    switch (led)
    {
        case LED1:      return LED1_PIN;
        case LED2:      return LED2_PIN;
        case LED_ALL:   return (LED1_PIN | LED2_PIN);
        default:        return 0;
    }
}

void LED_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    GPIO_InitStructure.GPIO_Pin   = LED1_PIN | LED2_PIN;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(LED_PORT, &GPIO_InitStructure);

    GPIO_ResetBits(LED_PORT, LED1_PIN | LED2_PIN); /* 默认熄灭 */
}

void LED_On(LED_TypeDef led)
{
    GPIO_SetBits(LED_PORT, LED_PinGet(led));
}

void LED_Off(LED_TypeDef led)
{
    GPIO_ResetBits(LED_PORT, LED_PinGet(led));
}

void LED_Toggle(LED_TypeDef led)
{
    uint16_t pins = LED_PinGet(led);
    GPIO_Write(LED_PORT, (uint16_t)(GPIO_ReadOutputData(LED_PORT) ^ pins));
}

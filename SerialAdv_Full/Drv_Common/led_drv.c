/**
  ******************************************************************************
  * @file    Drv_Common/led_drv.c
  * @brief   板载 LED 与 RGB 灯条驱动
  *          - LED1 : PG14（红）  - LED2 : PG15（蓝）
  *          - RGB  : PG0=R, PG1=G, PG2=B
  *          全部为高电平点亮
  ******************************************************************************
  */

#include "led_drv.h"

#define LED_PORT        GPIOG
#define LED1_PIN        GPIO_Pin_14
#define LED2_PIN        GPIO_Pin_15
#define LED_MASK_ALL    (uint16_t)(LED1_PIN | LED2_PIN)

#define RGB_PORT        GPIOG
#define RGB_R_PIN       GPIO_Pin_0
#define RGB_G_PIN       GPIO_Pin_1
#define RGB_B_PIN       GPIO_Pin_2
#define RGB_MASK_ALL    (uint16_t)(RGB_R_PIN | RGB_G_PIN | RGB_B_PIN)

static uint16_t LED_PinGet(LED_TypeDef led)
{
    switch (led)
    {
        case LED1:    return LED1_PIN;
        case LED2:    return LED2_PIN;
        case LED_ALL: return LED_MASK_ALL;
        default:      return 0;
    }
}

void LED_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    GPIO_InitStructure.GPIO_Pin   = LED_MASK_ALL;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(LED_PORT, &GPIO_InitStructure);

    /* 上电默认熄灭 */
    GPIO_ResetBits(LED_PORT, LED_MASK_ALL);
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
    uint16_t odr  = (uint16_t)GPIO_ReadOutputData(LED_PORT);
    GPIO_Write(LED_PORT, (uint16_t)(odr ^ pins));
}

void RGB_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    GPIO_InitStructure.GPIO_Pin   = RGB_MASK_ALL;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(RGB_PORT, &GPIO_InitStructure);

    GPIO_ResetBits(RGB_PORT, RGB_MASK_ALL);
}

void RGB_Set(RGB_TypeDef color)
{
    uint16_t on = 0;

    switch (color)
    {
        case RGB_R:      on = RGB_R_PIN; break;
        case RGB_G:      on = RGB_G_PIN; break;
        case RGB_B:      on = RGB_B_PIN; break;
        case RGB_YELLOW: on = (uint16_t)(RGB_R_PIN | RGB_G_PIN); break;
        case RGB_ALL:    on = RGB_MASK_ALL; break;
        default:         on = 0; break;
    }

    GPIO_ResetBits(RGB_PORT, RGB_MASK_ALL);
    if (on != 0)
    {
        GPIO_SetBits(RGB_PORT, on);
    }
}

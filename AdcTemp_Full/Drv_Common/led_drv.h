/**
  ******************************************************************************
  * @file    Drv_Common/led_drv.h
  * @brief   板载 LED 与 RGB 灯条驱动（均挂 GPIOG）
  ******************************************************************************
  */

#ifndef __LED_DRV_H
#define __LED_DRV_H

#include "stm32f10x.h"

/* 板载指示灯：高电平点亮 */
typedef enum
{
    LED1 = 0,       /* PG14 红色指示灯 */
    LED2,           /* PG15 蓝色指示灯 */
    LED_ALL         /* LED1 + LED2 */
} LED_TypeDef;

/* RGB 灯条（LRGB / J6 接口）：高电平点亮 */
typedef enum
{
    RGB_NONE = 0,   /* 全灭 */
    RGB_R,          /* PG0 */
    RGB_G,          /* PG1 */
    RGB_B,          /* PG2 */
    RGB_YELLOW,     /* R + G */
    RGB_CYAN,       /* G + B */
    RGB_MAGENTA,    /* R + B */
    RGB_ALL         /* R + G + B */
} RGB_TypeDef;

void LED_Init(void);
void LED_On(LED_TypeDef led);
void LED_Off(LED_TypeDef led);
void LED_Toggle(LED_TypeDef led);

void RGB_Init(void);
void RGB_Set(RGB_TypeDef color);

/* 供软件 PWM（呼吸灯）直接操作 RGB 引脚用：端口与三色总掩码 */
#define RGB_GPIO_PORT   GPIOG
#define RGB_PIN_MASK    (uint16_t)(GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2)

/* ============ 右 RGB 转向灯（原理图网络 RLED / L2，PE2=R PE3=G PE4=B）============ */
void RGB2_Init(void);
void RGB2_Set(RGB_TypeDef color);

#endif /* __LED_DRV_H */

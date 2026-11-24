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

/* 板载左灯珠 TLED（原理图 L1，网络 LRGB-R / LRGB-G / LRGB-B，各经 150R 限流）
 * 高电平点亮。⚠ 绿色通道在 PE7（GPIOE），与另外两路不同端口。 */
typedef enum
{
    RGB_NONE = 0,   /* 全灭 */
    RGB_R,          /* PG1 = LRGB-R 红色通道 */
    RGB_G,          /* PE7 = LRGB-G 绿色通道 */
    RGB_B,          /* PG2 = LRGB-B 蓝色通道 */
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

/* 供软件 PWM（呼吸灯）直接操作左灯珠用。
 * ⚠ 绿色通道在 PE7（GPIOE），单端口掩码表达不了，所以呼吸灯只驱动 GPIOG 上的通道；
 *   绿色通道由 RGB_Set() 负责。 */
#define RGB_GPIO_PORT   GPIOG
#define RGB_PIN_MASK    (uint16_t)(GPIO_Pin_1 | GPIO_Pin_2)
#define RGB_G_GPIO_PORT GPIOE
#define RGB_G_PIN_MASK  (uint16_t)GPIO_Pin_7

/* ★ 呼吸灯专用掩码：**只驱动红色通道 PG1**。
 * 任务书需求2 要求"左转向灯（红色）呈现呼吸灯的效果"。
 * ⚠ 千万别用 RGB_PIN_MASK(PG1|PG2)：那是红+蓝 = **紫色**，不是红色。
 *   2026-09-18 实测踩过这个坑——板子上看到的是一颗紫色呼吸灯，与任务书不符。 */
#define RGB_BREATH_PIN_MASK (uint16_t)GPIO_Pin_1

/* ============ 右 RGB 转向灯（原理图网络 RLED / L2，PE2=R PE3=G PE4=B）============ */
void RGB2_Init(void);
void RGB2_Set(RGB_TypeDef color);

#endif /* __LED_DRV_H */

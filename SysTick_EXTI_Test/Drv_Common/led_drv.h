/**
  ******************************************************************************
  * @file    Drv_Common/led_drv.h
  * @author  陈相林 (智能3班)
  * @brief   LED 驱动头文件
  ******************************************************************************
  */

#ifndef __LED_DRV_H
#define __LED_DRV_H

#include "stm32f10x.h"

typedef enum
{
    LED1 = 0,
    LED2,
    LED_ALL
} LED_TypeDef;

void LED_Init(void);
void LED_On(LED_TypeDef led);
void LED_Off(LED_TypeDef led);
void LED_Toggle(LED_TypeDef led);

#endif /* __LED_DRV_H */

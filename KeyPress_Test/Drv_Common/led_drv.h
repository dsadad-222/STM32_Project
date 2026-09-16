/**
  ******************************************************************************
  * @file    Drv_Common/led_drv.h
  * @brief   LED driver header (bare-register style).
  *          PG14 / PG15 high-active.
  ******************************************************************************
  */

#ifndef LED_DRV_H
#define LED_DRV_H

#include "stm32f10x.h"

typedef enum {
    LED_1 = 0,
    LED_2,
    LED_BOTH
} led_id_t;

void led_init(void);
void led_on(led_id_t id);
void led_off(led_id_t id);
void led_toggle(led_id_t id);

#endif

/*
 * led_drv.h
 * LED driver for PG14, PG15 (active high)
 */

#ifndef LED_DRV_H
#define LED_DRV_H

#include "stm32f10x.h"

#define LED_1    0x01
#define LED_2    0x02
#define LED_BOTH 0x03

void led_init(void);
void led_on(uint8_t id);
void led_off(uint8_t id);
void led_toggle(uint8_t id);

#endif

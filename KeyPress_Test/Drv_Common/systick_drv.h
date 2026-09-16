/**
  ******************************************************************************
  * @file    Drv_Common/systick_drv.h
  * @brief   1 ms SysTick tick provider.
  ******************************************************************************
  */

#ifndef SYSTICK_DRV_H
#define SYSTICK_DRV_H

#include <stdint.h>

void     systick_init_1ms(void);
uint32_t get_tick_ms(void);

#endif

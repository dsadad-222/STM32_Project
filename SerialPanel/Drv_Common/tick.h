/**
  ******************************************************************************
  * @file    Drv_Common/tick.h
  * @brief   1 ms system tick built directly on the Cortex-M3 SysTick timer.
  ******************************************************************************
  */

#ifndef TICK_H
#define TICK_H

#include <stdint.h>

/* Free running millisecond counter, incremented inside SysTick_Handler. */
extern volatile uint32_t g_ms_tick;

void     tick_init(void);
uint32_t tick_ms(void);
void     tick_delay_ms(uint32_t ms);

#endif /* TICK_H */

/**
  ******************************************************************************
  * @file    Drv_Common/systick_drv.c
  * @brief   Configure SysTick for a 1 ms interrupt; tick counter
  *          incremented inside the SysTick handler (see stm32f10x_it.c).
  ******************************************************************************
  */

#include "systick_drv.h"
#include "stm32f10x.h"

volatile uint32_t tick_ms = 0;

void systick_init_1ms(void)
{
    (void)SysTick_Config(SystemCoreClock / 1000U);
}

uint32_t get_tick_ms(void)
{
    return tick_ms;
}

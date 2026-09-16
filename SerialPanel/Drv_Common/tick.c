/**
  ******************************************************************************
  * @file    Drv_Common/tick.c
  * @brief   1 ms tick source. SysTick is programmed through its own registers,
  *          so no standard peripheral library call is involved here.
  ******************************************************************************
  */

#include "tick.h"
#include "stm32f10x.h"

volatile uint32_t g_ms_tick = 0U;

void tick_init(void)
{
    uint32_t reload = (SystemCoreClock / 1000U) - 1U;

    SysTick->LOAD = reload;     /* count down for exactly 1 ms          */
    SysTick->VAL  = 0U;         /* clear current value and COUNTFLAG    */
    SysTick->CTRL = 0x7U;       /* CLKSOURCE=1, TICKINT=1, ENABLE=1     */
}

uint32_t tick_ms(void)
{
    return g_ms_tick;
}

/* Blocking delay used only for start-up feedback. */
void tick_delay_ms(uint32_t ms)
{
    uint32_t start = g_ms_tick;

    while ((uint32_t)(g_ms_tick - start) < ms)
    {
        __NOP();
    }
}

/*
 * systick_drv.c
 * Configure SysTick as 1 ms interrupt, increment global ms counter
 */

#include "systick_drv.h"
#include "stm32f10x.h"

volatile uint64_t sys_ms = 0;

void systick_init(void)
{
    if (SysTick_Config(SystemCoreClock / 1000) != 0) {
        while (1); /* bad config */
    }
}

uint64_t sys_runtime_ms(void)
{
    return sys_ms;
}

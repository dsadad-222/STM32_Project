#include "dwt.h"
#include "stm32f10x.h"

/* Cortex-M3 debug/trace registers, accessed by raw address */
#define DWT_DEMCR   (*(volatile uint32_t *)0xE000EDFC)
#define DWT_CTRL    (*(volatile uint32_t *)0xE0001000)
#define DWT_CYCCNT  (*(volatile uint32_t *)0xE0001004)

#define TRCENA_BIT    (1u << 24)
#define CYCCNTENA_BIT (1u << 0)

void dwt_timer_start(void)
{
    DWT_DEMCR  |= TRCENA_BIT;    /* power up the trace block */
    DWT_CYCCNT  = 0;             /* clear the free-running counter */
    DWT_CTRL   |= CYCCNTENA_BIT; /* let it count */
}

void dwt_udelay(uint32_t us)
{
    uint32_t base = DWT_CYCCNT;
    uint32_t span = us * (SystemCoreClock / 1000000u);
    while ((uint32_t)(DWT_CYCCNT - base) < span) {
        /* spin until span clock cycles have elapsed */
    }
}

void dwt_mdelay(uint32_t ms)
{
    while (ms--) {
        dwt_udelay(1000u);
    }
}

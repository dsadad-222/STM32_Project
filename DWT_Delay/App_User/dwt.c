#include "dwt.h"
#include "stm32f10x.h"

/* Cortex-M3 DWT 内核寄存器
 * 0xE0001000  DWT_CTRL    控制寄存器
 * 0xE0001004  DWT_CYCCNT  32-bit 向上计数器
 */
#define REG_DWT_CTRLR    (*(volatile uint32_t *)0xE0001000)
#define REG_DWT_CYCCNTR  (*(volatile uint32_t *)0xE0001004)

void DelayInit(void)
{
    /* 1) 使能 DWT 模块 (DEMCR.TRCENA = 1) */
    CoreDebug->DEMCR |= (uint32_t)CoreDebug_DEMCR_TRCENA_Msk;

    /* 2) 先清再置 CYCCNTENA，确保计数器从 0 开始 */
    REG_DWT_CTRLR &= ~((uint32_t)1u << 0);
    REG_DWT_CTRLR |=  (uint32_t)1u << 0;

    /* 3) 计数器清零 */
    REG_DWT_CYCCNTR = 0;
}

void DelayNus(uint32_t nUs)
{
    uint32_t tickStart = REG_DWT_CYCCNTR;
    /* 把 us 换算成 cycle 数：1us 对应 SystemCoreClock/1000000 个 cycle */
    nUs *= (uint32_t)(SystemCoreClock / 1000000u);

    /* 等到计数器走过 nUs 个 cycle 为止 (无符号回绕安全) */
    while ((REG_DWT_CYCCNTR - tickStart) < nUs) {
        /* busy-wait */
    }
}

void DelayNms(uint32_t nMs)
{
    /* 1ms = 1000us，逐毫秒延时会自动处理大数回绕 */
    for (uint32_t i = 0; i < nMs; ++i) {
        DelayNus(1000u);
    }
}

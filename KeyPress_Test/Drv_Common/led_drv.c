/**
  ******************************************************************************
  * @file    Drv_Common/led_drv.c
  * @brief   LED driver implementation, direct register access on GPIOG.
  *          - PG14 / PG15 push-pull output, 50MHz
  *          - BSRR/BRR for set/reset (atomic on Cortex-M3)
  ******************************************************************************
  */

#include "led_drv.h"

#define LED_GPIO            ((GPIO_TypeDef *)GPIOG_BASE)
#define LED1_MASK           ((uint16_t)(1u << 14))
#define LED2_MASK           ((uint16_t)(1u << 15))

static inline uint16_t led_mask(led_id_t id)
{
    switch (id) {
        case LED_1:    return LED1_MASK;
        case LED_2:    return LED2_MASK;
        case LED_BOTH: return (uint16_t)(LED1_MASK | LED2_MASK);
        default:       return 0;
    }
}

void led_init(void)
{
    /* Enable GPIOG peripheral clock */
    RCC->APB2ENR |= RCC_APB2ENR_IOPGEN;

    /* PG14 / PG15: CNF=00 push-pull output, MODE=11 50MHz -> 0x3 per pin */
    LED_GPIO->CRH &= (uint32_t)~(0xFFu << ((14 - 8) * 4));
    LED_GPIO->CRH |=  (uint32_t)(0x33u << ((14 - 8) * 4));

    /* Default off */
    LED_GPIO->BRR = (uint32_t)(LED1_MASK | LED2_MASK);
}

void led_on(led_id_t id)
{
    LED_GPIO->BSRR = led_mask(id);
}

void led_off(led_id_t id)
{
    LED_GPIO->BRR = led_mask(id);
}

void led_toggle(led_id_t id)
{
    uint16_t m = led_mask(id);
    LED_GPIO->ODR ^= m;
}

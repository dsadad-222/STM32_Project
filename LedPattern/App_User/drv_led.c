#include "drv_led.h"
#include "stm32f10x.h"

/* hardware description for every led (port + bit) */
typedef struct {
    GPIO_TypeDef *port;
    uint16_t      pin;
} led_hw_t;

static const led_hw_t g_led[] = {
    { GPIOG, 1u << 14 },  /* L_LED1 */
    { GPIOG, 1u << 15 },  /* L_LED2 */
    { GPIOG, 1u << 0  },  /* L_RG_R */
    { GPIOG, 1u << 1  },  /* L_RG_G */
    { GPIOG, 1u << 2  },  /* L_RG_B */
    { GPIOE, 1u << 2  },  /* L_RR_R */
    { GPIOE, 1u << 3  },  /* L_RR_G */
    { GPIOE, 1u << 4  },  /* L_RR_B */
};

void led_driver_init(void)
{
    RCC->APB2ENR |= (1u << 8) | (1u << 6);   /* GPIOG + GPIOE clock */

    /* GPIOG: PG0/1/2 and PG14/15 -> push-pull 50MHz (MODE=11 CNF=00) */
    GPIOG->CRL = (GPIOG->CRL & ~0x00000FFFu) | 0x00000333u;
    GPIOG->CRH = (GPIOG->CRH & ~0xFF000000u) | 0x33000000u;

    /* GPIOE: PE2/3/4 -> push-pull 50MHz */
    GPIOE->CRL = (GPIOE->CRL & ~0x000FFF00u) | 0x00033300u;
}

void led_turn_on(led_id_t id)
{
    g_led[id].port->BSRR = g_led[id].pin;
}

void led_turn_off(led_id_t id)
{
    g_led[id].port->BRR = g_led[id].pin;
}

void led_toggle(led_id_t id)
{
    GPIO_TypeDef *p = g_led[id].port;
    if (p->ODR & g_led[id].pin)
        p->BRR = g_led[id].pin;
    else
        p->BSRR = g_led[id].pin;
}

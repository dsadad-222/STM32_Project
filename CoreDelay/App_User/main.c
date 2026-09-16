/* chapter4 task3 - DWT hardware delay
 * MCU: STM32F103ZET6 (Cortex-M3, SYSCLK = 72MHz by default)
 * demo: LED1 (PG14) blinks at ~1Hz using DWT_CYCCNT timing
 */
#include "stm32f10x.h"
#include "dwt.h"

#define LED1_BIT (1u << 14)

static void led_gpio_setup(void)
{
    RCC->APB2ENR |= (1u << 8);                              /* GPIOG clock on */
    GPIOG->CRH = (GPIOG->CRH & ~(0x0Fu << 24)) | (0x03u << 24);
}

int main(void)
{
    led_gpio_setup();
    dwt_timer_start();

    for (;;) {
        GPIOG->ODR ^= LED1_BIT;   /* flip LED1 state */
        dwt_mdelay(500);
    }
}

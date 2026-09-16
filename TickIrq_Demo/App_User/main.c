/*
 * main.c
 * SysTick tick + EXTI key demo
 * - 500 ms running LED pattern (LED1 / LED2 alternate)
 * - Keys: PG3 toggles LED1, PG4 toggles LED2, PG5 toggles both
 */

#include "led_drv.h"
#include "exti_drv.h"
#include "systick_drv.h"

int main(void)
{
    uint64_t last_ms;
    uint8_t state;

    led_init();
    exti_key_init();
    systick_init();

    last_ms = sys_runtime_ms();
    state = 0;
    led_on(LED_1);

    while (1) {
        if (sys_runtime_ms() - last_ms > 500) {
            last_ms = sys_runtime_ms();
            state ^= 1;
            if (state) {
                led_on(LED_2);
                led_off(LED_1);
            } else {
                led_on(LED_1);
                led_off(LED_2);
            }
        }
    }
}

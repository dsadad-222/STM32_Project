/* chapter4 task4 - flowing light architecture (driver + app layers)
 * MCU: STM32F103ZET6 (Cortex-M3)
 * app layer only builds light patterns; the driver handles gpio
 */
#include "stm32f10x.h"
#include "drv_led.h"

static void soft_delay(uint32_t cyc)
{
    for (volatile uint32_t i = 0; i < cyc; ++i) {
        /* empty spin loop, tuned for ~72MHz core */
    }
}

/* order in which the 8 leds chase */
static const led_id_t g_seq[] = {
    L_LED1, L_LED2, L_RG_R, L_RG_G, L_RG_B, L_RR_R, L_RR_G, L_RR_B
};

int main(void)
{
    led_driver_init();

    for (;;) {
        /* running light: light one, wait, clear it */
        for (uint32_t i = 0; i < 8; ++i) {
            led_turn_on(g_seq[i]);
            soft_delay(1800000u);
            led_turn_off(g_seq[i]);
        }

        /* all-on burst, then all-off, as a return beat */
        for (uint32_t i = 0; i < 8; ++i) led_turn_on(g_seq[i]);
        soft_delay(2500000u);
        for (uint32_t i = 0; i < 8; ++i) led_turn_off(g_seq[i]);
        soft_delay(2500000u);
    }
}

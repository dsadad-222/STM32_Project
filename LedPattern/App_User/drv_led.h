#ifndef LED_DRIVER_H
#define LED_DRIVER_H

#include <stdint.h>

typedef enum {
    L_LED1 = 0,
    L_LED2,
    L_RG_R, L_RG_G, L_RG_B,
    L_RR_R, L_RR_G, L_RR_B
} led_id_t;

/* enable clocks and configure all 8 pins as push-pull output */
void led_driver_init(void);

/* assert one led */
void led_turn_on(led_id_t id);

/* clear one led */
void led_turn_off(led_id_t id);

/* invert the current state of one led */
void led_toggle(led_id_t id);

#endif

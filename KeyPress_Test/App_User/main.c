/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   Single-button multi-action LED control.
  *          KEY1(PG3) CLICK    -> LED1(PG14) latched on
  *          KEY1(PG3) DBLCLICK -> LED2(PG15) latched on
  *          KEY1(PG3) LONG     -> both LEDs off
  *
  *          1 ms SysTick tick, 10 ms button poll period.
  ******************************************************************************
  */

#include "led_drv.h"
#include "key_drv.h"
#include "systick_drv.h"

#define POLL_MS     10u

static key_t s_key1;

static void handle_key1(key_event_t evt)
{
    switch (evt)
    {
        case KEY_EVT_CLICK:        led_on(LED_1);    break;  /* click  -> LED1 latched */
        case KEY_EVT_DBLCLICK:     led_on(LED_2);    break;  /* dblclick -> LED2 latched */
        case KEY_EVT_LONG_END:     led_off(LED_BOTH); break;  /* long release -> all off */
        default: break;
    }
}

int main(void)
{
    uint32_t last_scan = 0;

    led_init();
    key_init(&s_key1, GPIOG, 3, 1);  /* PG3 active-low */
    systick_init_1ms();

    while (1)
    {
        uint32_t now = get_tick_ms();

        if (now - last_scan >= POLL_MS)
        {
            last_scan = now;
            key_poll(&s_key1);
            key_event_t evt = key_get_event(&s_key1);
            if (evt != KEY_EVT_NONE)
            {
                handle_key1(evt);
            }
        }
    }
}

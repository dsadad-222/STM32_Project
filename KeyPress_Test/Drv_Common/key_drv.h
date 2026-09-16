/**
  ******************************************************************************
  * @file    Drv_Common/key_drv.h
  * @brief   Key scan driver (bare register, FSM + debounce).
  *          Short press / long press / single click / double click detection.
  *          Caller polls key_poll() every 10~20 ms.
  ******************************************************************************
  */

#ifndef KEY_DRV_H
#define KEY_DRV_H

#include "stm32f10x.h"

#define KEY_DEBOUNCE_MS      20
#define KEY_SHORT_LONG_MS    1000
#define KEY_DBLCLICK_GAP_MS  300

typedef enum {
    KEY_EVT_NONE = 0,
    KEY_EVT_CLICK,
    KEY_EVT_DBLCLICK,
    KEY_EVT_LONG_START,
    KEY_EVT_LONG_END
} key_event_t;

typedef enum {
    KS_IDLE = 0,
    KS_DEBOUNCE_DN,
    KS_PRESSED,
    KS_CLICK_WAIT2,
    KS_DBLCLICK,
    KS_LONG_HOLD
} key_state_t;

typedef struct {
    GPIO_TypeDef *port;
    uint16_t      bit_mask;     /* 1 << pin */
    uint8_t       active_low;   /* 1 if pressed level is low */

    uint8_t       raw;
    uint8_t       debounced;
    uint8_t       prev_debounced;
    uint32_t      raw_changed_at;

    key_state_t   state;
    uint32_t      pressed_at;
    uint32_t      released_at;
    uint8_t       long_hold;

    key_event_t   event;
} key_t;

void         key_init(key_t *k, GPIO_TypeDef *port, uint16_t pin, uint8_t active_low);
void         key_poll(key_t *k);
key_event_t  key_get_event(key_t *k);
uint8_t      key_in_long_hold(key_t *k);

#endif

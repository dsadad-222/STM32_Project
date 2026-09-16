/**
  ******************************************************************************
  * @file    Drv_Common/key_drv.c
  * @brief   Key scan implementation (bare register).
  *          Polled FSM: IDLE -> DEBOUNCE_DN -> PRESSED ->
  *          (CLICK_WAIT2 | LONG_HOLD) -> DBLCLICK | (CLICK | LONG_END).
  ******************************************************************************
  */

#include "key_drv.h"
#include "systick_drv.h"

static inline uint8_t read_raw(key_t *k)
{
    uint8_t bit = (k->port->IDR & k->bit_mask) ? 1u : 0u;
    return k->active_low ? (uint8_t)!bit : bit;
}

static inline void configure_input_pu(GPIO_TypeDef *port, uint16_t pin, uint16_t mask)
{
    /* CNFy=10 (input with pull-up/pull-down), MODEy=00 (input) -> nibble = 0x8 */
    if (pin < 8) {
        port->CRL &= ~(0xFu << (pin * 4u));
        port->CRL |=  (0x8u << (pin * 4u));
    } else {
        port->CRH &= ~(0xFu << ((pin - 8u) * 4u));
        port->CRH |=  (0x8u << ((pin - 8u) * 4u));
    }
    /* ODR=1 selects pull-up */
    port->BSRR = mask;
}

static inline void enable_port_clock(GPIO_TypeDef *port)
{
    if      (port == GPIOA) RCC->APB2ENR |= RCC_APB2ENR_IOPAEN;
    else if (port == GPIOB) RCC->APB2ENR |= RCC_APB2ENR_IOPBEN;
    else if (port == GPIOC) RCC->APB2ENR |= RCC_APB2ENR_IOPCEN;
    else if (port == GPIOD) RCC->APB2ENR |= RCC_APB2ENR_IOPDEN;
    else if (port == GPIOE) RCC->APB2ENR |= RCC_APB2ENR_IOPEEN;
    else if (port == GPIOF) RCC->APB2ENR |= RCC_APB2ENR_IOPFEN;
    else if (port == GPIOG) RCC->APB2ENR |= RCC_APB2ENR_IOPGEN;
}

void key_init(key_t *k, GPIO_TypeDef *port, uint16_t pin, uint8_t active_low)
{
    k->port             = port;
    k->bit_mask         = (uint16_t)(1u << pin);
    k->active_low       = active_low;
    k->raw              = 1u;
    k->debounced        = 1u;
    k->prev_debounced   = 1u;
    k->raw_changed_at   = 0u;
    k->state            = KS_IDLE;
    k->pressed_at       = 0u;
    k->released_at      = 0u;
    k->long_hold        = 0u;
    k->event            = KEY_EVT_NONE;

    enable_port_clock(port);
    configure_input_pu(port, pin, k->bit_mask);
}

void key_poll(key_t *k)
{
    uint32_t now = get_tick_ms();
    uint8_t  r   = read_raw(k);

    /* Debounce window */
    if (r != k->raw) {
        if (k->raw_changed_at == 0u) {
            k->raw_changed_at = now;
        } else if (now - k->raw_changed_at >= KEY_DEBOUNCE_MS) {
            k->debounced      = r;
            k->raw            = r;
            k->raw_changed_at = 0u;
        }
    } else {
        k->raw_changed_at = 0u;
    }

    /* Edge detect on debounced level */
    if (k->debounced != k->prev_debounced) {
        uint8_t prev = k->prev_debounced;
        k->prev_debounced = k->debounced;
        if (k->debounced && !prev) {
            k->pressed_at = now;
            k->state = (k->state == KS_CLICK_WAIT2) ? KS_DBLCLICK : KS_DEBOUNCE_DN;
        }
    }

    switch (k->state) {
        case KS_IDLE:
            break;

        case KS_DEBOUNCE_DN:
            k->state = KS_PRESSED;
            break;

        case KS_PRESSED:
            if (now - k->pressed_at >= KEY_SHORT_LONG_MS) {
                k->state     = KS_LONG_HOLD;
                k->long_hold = 1u;
                k->event     = KEY_EVT_LONG_START;
            } else if (k->debounced == 0u) {
                k->state       = KS_CLICK_WAIT2;
                k->released_at = now;
            }
            break;

        case KS_CLICK_WAIT2:
            if (now - k->released_at >= KEY_DBLCLICK_GAP_MS) {
                k->state = KS_IDLE;
                k->event = KEY_EVT_CLICK;
            }
            break;

        case KS_DBLCLICK:
            k->state = KS_IDLE;
            k->event = KEY_EVT_DBLCLICK;
            break;

        case KS_LONG_HOLD:
            if (k->debounced == 0u) {
                k->state     = KS_IDLE;
                k->long_hold = 0u;
                k->event     = KEY_EVT_LONG_END;
            }
            break;

        default:
            k->state = KS_IDLE;
            break;
    }
}

key_event_t key_get_event(key_t *k)
{
    key_event_t e = k->event;
    k->event = KEY_EVT_NONE;
    return e;
}

uint8_t key_in_long_hold(key_t *k)
{
    return k->long_hold;
}

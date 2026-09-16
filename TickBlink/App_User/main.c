// chapter5 lab: systick-based 1ms tick driving a LED blink
// board: STM32F103ZET6, LED1 on PG14 (active high, common-cathode)
#include "stm32f10x.h"

// free-running millisecond counter, updated inside the systick ISR (stm32f10x_it.c)
volatile uint32_t ms_counter = 0;

// configure cortex-M3 systick to fire every 1 ms
static void systick_start(void)
{
    // LOAD = core_clock / 1000  ->  72000 counts at 72 MHz
    // SysTick_Config() writes LOAD, clears VAL, enables core clock + interrupt
    if (SysTick_Config(SystemCoreClock / 1000)) {
        for (;;) { /* config error trap */ }
    }
}

// blocking delay measured against the systick millisecond counter
static void wait_ms(uint32_t ms)
{
    uint32_t base = ms_counter;
    while ((ms_counter - base) < ms) {
        /* spin until the tick count advances enough */
    }
}

// configure PG14 as push-pull output by writing the register directly
static void led_setup(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_IOPGEN;          // turn on GPIOG clock
    // PG14 sits in CRH bits [27:24]; MODE=11 (50MHz), CNF=00 (push-pull)
    GPIOG->CRH &= ~(0x0F << (4 * (14 - 8)));
    GPIOG->CRH |=  (0x03 << (4 * (14 - 8)));
}

static void led_on(void)  { GPIOG->BSRR = GPIO_Pin_14; }
static void led_off(void) { GPIOG->BRR  = GPIO_Pin_14; }

int main(void)
{
    led_setup();
    systick_start();

    for (;;) {
        led_on();
        wait_ms(500);
        led_off();
        wait_ms(500);
    }
}

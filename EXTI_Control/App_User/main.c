/*
 * External interrupt demo on STM32F103ZE.
 * Falling edge on KEY1/2/3 (PG3/4/5) toggles LED1/2 (PG14/15).
 * Standard peripheral library V3.6 is used only for register access wrappers.
 */

#include "stm32f10x.h"

/* LED resources on GPIOG. */
#define LED1_PIN    GPIO_Pin_14
#define LED2_PIN    GPIO_Pin_15
#define LED_ALL     (LED1_PIN | LED2_PIN)

/* KEY resources on GPIOG. */
#define KEY1_PIN    GPIO_Pin_3
#define KEY2_PIN    GPIO_Pin_4
#define KEY3_PIN    GPIO_Pin_5
#define KEY_ALL     (KEY1_PIN | KEY2_PIN | KEY3_PIN)

/* Local helpers. */
static void led_init(void)
{
    GPIO_InitTypeDef cfg;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    cfg.GPIO_Pin   = LED_ALL;
    cfg.GPIO_Mode  = GPIO_Mode_Out_PP;
    cfg.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOG, &cfg);

    GPIO_ResetBits(GPIOG, LED_ALL);
}

static void key_init(void)
{
    GPIO_InitTypeDef cfg;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG | RCC_APB2Periph_AFIO, ENABLE);

    cfg.GPIO_Pin  = KEY_ALL;
    cfg.GPIO_Mode = GPIO_Mode_IPU;
    GPIO_Init(GPIOG, &cfg);
}

static void exti_init(void)
{
    EXTI_InitTypeDef exti;
    NVIC_InitTypeDef nvic;

    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource3);
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource4);
    GPIO_EXTILineConfig(GPIO_PortSourceGPIOG, GPIO_PinSource5);

    exti.EXTI_Line    = EXTI_Line3 | EXTI_Line4 | EXTI_Line5;
    exti.EXTI_Mode    = EXTI_Mode_Interrupt;
    exti.EXTI_Trigger = EXTI_Trigger_Falling;
    exti.EXTI_LineCmd = ENABLE;
    EXTI_Init(&exti);

    NVIC_PriorityGroupConfig(NVIC_PriorityGroup_1);

    nvic.NVIC_IRQChannel                   = EXTI3_IRQn;
    nvic.NVIC_IRQChannelPreemptionPriority = 1;
    nvic.NVIC_IRQChannelSubPriority        = 0;
    nvic.NVIC_IRQChannelCmd                = ENABLE;
    NVIC_Init(&nvic);

    nvic.NVIC_IRQChannel                   = EXTI4_IRQn;
    nvic.NVIC_IRQChannelSubPriority        = 1;
    NVIC_Init(&nvic);

    nvic.NVIC_IRQChannel                   = EXTI9_5_IRQn;
    nvic.NVIC_IRQChannelSubPriority        = 2;
    NVIC_Init(&nvic);
}

static inline void led_toggle(uint16_t pin)
{
    if (GPIO_ReadOutputDataBit(GPIOG, pin) == Bit_RESET)
        GPIO_SetBits(GPIOG, pin);
    else
        GPIO_ResetBits(GPIOG, pin);
}

/* KEY1 -> toggle LED1 */
void EXTI3_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line3) != RESET) {
        led_toggle(LED1_PIN);
        EXTI_ClearITPendingBit(EXTI_Line3);
    }
}

/* KEY2 -> toggle LED2 */
void EXTI4_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line4) != RESET) {
        led_toggle(LED2_PIN);
        EXTI_ClearITPendingBit(EXTI_Line4);
    }
}

/* KEY3 -> toggle both LEDs (EXTI9_5 shared IRQ) */
void EXTI9_5_IRQHandler(void)
{
    if (EXTI_GetITStatus(EXTI_Line5) != RESET) {
        led_toggle(LED1_PIN);
        led_toggle(LED2_PIN);
        EXTI_ClearITPendingBit(EXTI_Line5);
    }
}

int main(void)
{
    led_init();
    key_init();
    exti_init();

    for (;;) {
        /* All work is done in ISRs. */
    }
}

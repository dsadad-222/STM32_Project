#include <stdint.h>

void SystemInit(void)
{
}

#define GPIOG_BASE  0x40012000UL
#define RCC_BASE    0x40021000UL

#define GPIOG_CRL   (*(volatile uint32_t *)(GPIOG_BASE + 0x00))
#define GPIOG_CRH   (*(volatile uint32_t *)(GPIOG_BASE + 0x04))	
#define GPIOG_IDR   (*(volatile uint32_t *)(GPIOG_BASE + 0x08))
#define GPIOG_ODR   (*(volatile uint32_t *)(GPIOG_BASE + 0x0C))
#define GPIOG_BSRR  (*(volatile uint32_t *)(GPIOG_BASE + 0x10))
#define GPIOG_BRR   (*(volatile uint32_t *)(GPIOG_BASE + 0x14))

#define RCC_APB2ENR (*(volatile uint32_t *)(RCC_BASE + 0x18))

#define LED1_PIN  14
#define LED2_PIN  15
#define KEY1_PIN  3
#define KEY2_PIN  4
#define KEY3_PIN  5

#define KEY_INPUT_MODE  0x04

#define CURRENT_TASK  3

static void Delay(uint32_t count)
{
    while (count--) ;
}

static void GPIO_Init(void)
{
    RCC_APB2ENR |= (1u << 8);

    /* PG14/PG15 -> 推挽输出 50MHz (CNF=00,MODE=11 => 0x3) */
    GPIOG_CRH = (GPIOG_CRH & ~((uint32_t)0xFFu << 24)) | ((uint32_t)0x33u << 24);
    /* PG3/PG4/PG5 -> 输入模式 (KEY_INPUT_MODE 决定浮空/上拉) */
    uint32_t crl_in = (KEY_INPUT_MODE == 0x08) ? 0x888u : 0x444u;
    GPIOG_CRL = (GPIOG_CRL & ~((uint32_t)0xFFFu << 12)) | (crl_in << 12);

#if KEY_INPUT_MODE == 0x08
    GPIOG_BSRR = (1u << KEY1_PIN) | (1u << KEY2_PIN) | (1u << KEY3_PIN);
#endif
}

static uint8_t GetKeyVal(void)
{
    uint8_t val = 0;
#if KEY_INPUT_MODE == 0x08
    if ((GPIOG_IDR & (1u << KEY1_PIN)) == 0) val |= 0x01;
    if ((GPIOG_IDR & (1u << KEY2_PIN)) == 0) val |= 0x02;
    if ((GPIOG_IDR & (1u << KEY3_PIN)) == 0) val |= 0x04;
#else
    if ( GPIOG_IDR & (1u << KEY1_PIN) ) val |= 0x01;
    if ( GPIOG_IDR & (1u << KEY2_PIN) ) val |= 0x02;
    if ( GPIOG_IDR & (1u << KEY3_PIN) ) val |= 0x04;
#endif
    return val;
}

static inline uint8_t KeyDown(uint8_t keyVal, uint32_t pin)
{
    return (keyVal & (1u << (pin - 3))) ? 1u : 0u;
}

int main(void)
{
    GPIO_Init();

#if CURRENT_TASK == 2
    while (1)
    {
        GPIOG_BSRR = (1u << LED1_PIN);
        Delay(0x300000);
        GPIOG_BRR  = (1u << LED1_PIN);
        Delay(0x300000);
    }

#elif CURRENT_TASK == 3
    while (1)
    {
        uint8_t key = GetKeyVal();
        if (key & 0x01)
            GPIOG_ODR |= (1u << LED1_PIN);   /* 按下 KEY1 -> LED1 点亮 */
        else
            GPIOG_ODR &= ~(1u << LED1_PIN);  /* 松开 KEY1 -> LED1 熄灭 */
    }

#elif CURRENT_TASK == 4
    while (1)
    {
        uint8_t key = GetKeyVal();
        if (key & 0x01) GPIOG_BSRR = (1u << LED1_PIN);
        else            GPIOG_BRR  = (1u << LED1_PIN);

        if (key & 0x02) GPIOG_BSRR = (1u << LED2_PIN);
        else            GPIOG_BRR  = (1u << LED2_PIN);

        if (key & 0x04) GPIOG_BSRR = (1u << LED1_PIN) | (1u << LED2_PIN);
        else            GPIOG_BRR  = (1u << LED1_PIN) | (1u << LED2_PIN);
    }
#endif
}

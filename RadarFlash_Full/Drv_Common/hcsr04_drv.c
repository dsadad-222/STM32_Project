#include "hcsr04_drv.h"

/*
 * HC-SR04 时序：
 *   TRIG 拉高 >=10us -> 模块发 8 个 40kHz 脉冲
 *   ECHO 拉高，高电平时间 = 声波往返时间
 *   距离 = 高电平时间(us) * 0.343mm/us / 2 = us * 0.173mm
 * 量程 2cm~400cm 对应 ECHO 高电平约 116us~23000us。
 *
 * TIM4 配成 1MHz 自由计数(16 位, 65.5ms 绕回)。
 * 单次测量全程(触发 12us + 等上升 20ms + 高电平 26ms) < 65.5ms，
 * 每次测量前把计数器清零即可保证不绕回。
 */

#define HCSR04_TRIG_PORT     GPIOF
#define HCSR04_TRIG_PIN      GPIO_Pin_11
#define HCSR04_ECHO_PORT     GPIOF
#define HCSR04_ECHO_PIN      GPIO_Pin_12
#define HCSR04_RCC           RCC_APB2Periph_GPIOF

#define HCSR04_TRIG_US       12u     /* 触发脉冲宽度 */
#define HCSR04_WAIT_UP_US    20000u  /* 等 ECHO 上升沿超时 */
#define HCSR04_WAIT_DN_US    26000u  /* ECHO 高电平超时(4m 约 23ms) */
#define HCSR04_US_MIN        116u    /* 2cm */
#define HCSR04_US_MAX        24000u  /* 留一点余量 */

/* TIM4: 1MHz 自由计数，供本驱动与 nec_ir_drv 共用（重复配置幂等无害） */
static uint8_t  s_lastErr   = HCSR04_ERR_NONE;
static uint16_t s_lastRawUs = 0u;

static void Hcsr04_Tim4UsInit(void)
{
    TIM_TimeBaseInitTypeDef tim;

    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM4, ENABLE);

    tim.TIM_Prescaler     = 72u - 1u;   /* 72MHz / 72 = 1MHz -> 1us */
    tim.TIM_Period        = 0xFFFFu;
    tim.TIM_ClockDivision = TIM_CKD_DIV1;
    tim.TIM_CounterMode   = TIM_CounterMode_Up;
    TIM_TimeBaseInit(TIM4, &tim);
    TIM_SetCounter(TIM4, 0u);
    TIM_Cmd(TIM4, ENABLE);
}

void Hcsr04_Init(void)
{
    GPIO_InitTypeDef io;

    RCC_APB2PeriphClockCmd(HCSR04_RCC, ENABLE);

    /* TRIG: 推挽输出，默认低 */
    io.GPIO_Pin   = HCSR04_TRIG_PIN;
    io.GPIO_Mode  = GPIO_Mode_Out_PP;
    io.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(HCSR04_TRIG_PORT, &io);
    GPIO_ResetBits(HCSR04_TRIG_PORT, HCSR04_TRIG_PIN);

    /* ECHO: 浮空输入（FT 脚，5V 模块直连） */
    io.GPIO_Pin  = HCSR04_ECHO_PIN;
    io.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(HCSR04_ECHO_PORT, &io);

    Hcsr04_Tim4UsInit();
}

static void Hcsr04_DelayUs(uint16_t us)
{
    uint16_t start = (uint16_t)TIM_GetCounter(TIM4);

    while (((uint16_t)((uint16_t)TIM_GetCounter(TIM4) - start)) < us)
    {
        /* busy wait */
    }
}

static uint16_t Hcsr04_MeasureOnce(void)
{
    uint16_t start;
    uint16_t high;

    /* 1. 触发: TRIG 高 12us（先清零计数器，保证本全程不绕回） */
    TIM_SetCounter(TIM4, 0u);
    GPIO_SetBits(HCSR04_TRIG_PORT, HCSR04_TRIG_PIN);
    Hcsr04_DelayUs(HCSR04_TRIG_US);
    GPIO_ResetBits(HCSR04_TRIG_PORT, HCSR04_TRIG_PIN);

    /* 2. 等 ECHO 拉高 */
    start = (uint16_t)TIM_GetCounter(TIM4);
    while (GPIO_ReadInputDataBit(HCSR04_ECHO_PORT, HCSR04_ECHO_PIN) == Bit_RESET)
    {
        if (((uint16_t)((uint16_t)TIM_GetCounter(TIM4) - start)) > HCSR04_WAIT_UP_US)
        {
            s_lastErr   = HCSR04_ERR_NO_UP;
            s_lastRawUs = 0u;
            return 0xFFFFu;                 /* 无回波 */
        }
    }

    /* 3. 量高电平宽度 */
    start = (uint16_t)TIM_GetCounter(TIM4);
    while (GPIO_ReadInputDataBit(HCSR04_ECHO_PORT, HCSR04_ECHO_PIN) == Bit_SET)
    {
        if (((uint16_t)((uint16_t)TIM_GetCounter(TIM4) - start)) > HCSR04_WAIT_DN_US)
        {
            s_lastErr   = HCSR04_ERR_STUCK_HIGH;
            s_lastRawUs = 0xFFFFu;
            return 0xFFFFu;
        }
    }
    high = (uint16_t)((uint16_t)TIM_GetCounter(TIM4) - start);
    s_lastRawUs = high;

    /* 4. 换算 us -> mm */
    if (high > HCSR04_US_MAX)
    {
        s_lastErr = HCSR04_ERR_RANGE;
        return 0xFFFFu;
    }
    if (high < HCSR04_US_MIN)
    {
        s_lastErr = HCSR04_ERR_SHORT;
        return 0xFFFFu;
    }
    s_lastErr = HCSR04_ERR_NONE;
    return (uint16_t)(((uint32_t)high * 173u) / 1000u); /* 0.173 mm/us */
}

uint8_t Hcsr04_GetLastErr(void)
{
    return s_lastErr;
}

uint16_t Hcsr04_GetLastRawUs(void)
{
    return s_lastRawUs;
}

uint8_t Hcsr04_EchoLevel(void)
{
    return (GPIO_ReadInputDataBit(HCSR04_ECHO_PORT, HCSR04_ECHO_PIN) == Bit_SET) ? 1u : 0u;
}

uint16_t Hcsr04_GetDistanceMm(void)
{
    return Hcsr04_MeasureOnce();
}

uint16_t Hcsr04_GetDistanceMid3(void)
{
    uint16_t v[3];
    uint8_t  valid = 0;
    uint8_t  i;
    uint8_t  j;
    uint16_t t;

    for (i = 0u; i < 3u; i++)
    {
        uint16_t d = Hcsr04_MeasureOnce();

        if (d != 0xFFFFu)
        {
            v[valid] = d;
            valid++;
        }
    }

    if (valid == 0u)
    {
        return 0xFFFFu;
    }

    /* 插入排序后取中值，单次毛刺直接被挤掉 */
    for (i = 1u; i < valid; i++)
    {
        for (j = i; (j > 0u) && (v[j - 1u] > v[j]); j--)
        {
            t        = v[j - 1u];
            v[j - 1u] = v[j];
            v[j]     = t;
        }
    }
    return v[valid / 2u];
}

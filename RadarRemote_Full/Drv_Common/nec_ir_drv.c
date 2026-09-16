#include "nec_ir_drv.h"

/*
 * NEC 解码原理：
 *   EXTI11 配下降沿。HS0038B 空闲输出高，每收到一段载波就拉低，
 *   所以 NEC 的每个码元(引导/位/重复)都以一个下降沿开头。
 *   两个下降沿的时间差 TIM4 1MHz 计数(uint16 环绕减法自动处理单次绕回)：
 *     13.5ms -> 引导码；11.25ms -> 重复码；1.12ms -> bit0；2.25ms -> bit1
 *   空闲后的第一个下降沿间隔很长(标准遥控约 108ms)，绕回后得到一个
 *   不落在任何窗口里的大数 -> 走 default 复位收位状态。
 */

#define NEC_IR_PORT        GPIOG
#define NEC_IR_PIN         GPIO_Pin_11
#define NEC_IR_RCC         RCC_APB2Periph_GPIOG
#define NEC_IR_EXTI_PORT   GPIO_PortSourceGPIOG
#define NEC_IR_EXTI_PIN    GPIO_PinSource11

/* 下降沿间隔判定窗口 (us) */
#define NEC_US_LEAD_LO     12400u  /* 引导码 13.5ms 下限 */
#define NEC_US_LEAD_HI     14600u  /* 引导码 13.5ms 上限 */
#define NEC_US_RPT_LO      10500u  /* 重复码 11.25ms 下限 */
#define NEC_US_RPT_HI      12400u  /* 重复码 11.25ms 上限 */
#define NEC_US_B0_LO       850u    /* bit0 1.12ms */
#define NEC_US_B0_HI       1400u
#define NEC_US_B1_LO       1900u   /* bit1 2.25ms */
#define NEC_US_B1_HI       2700u

static volatile uint16_t s_lastFallUs;
static volatile uint32_t s_shift;
static volatile uint8_t  s_bitCnt;
static volatile uint8_t  s_frameReady;
static volatile uint32_t s_frame;
static volatile uint8_t  s_repeatCnt;

void NecIr_Init(void)
{
    GPIO_InitTypeDef  io;
    EXTI_InitTypeDef  exti;
    NVIC_InitTypeDef  nvic;
    TIM_TimeBaseInitTypeDef tim;

    RCC_APB2PeriphClockCmd(NEC_IR_RCC | RCC_APB2Periph_AFIO, ENABLE);

    /* PG11 上拉输入: HS0038B 空闲输出高，上拉让引脚空闲态确定 */
    io.GPIO_Pin   = NEC_IR_PIN;
    io.GPIO_Mode  = GPIO_Mode_IPU;
    io.GPIO_Speed = GPIO_Speed_2MHz;
    GPIO_Init(NEC_IR_PORT, &io);

    GPIO_EXTILineConfig(NEC_IR_EXTI_PORT, NEC_IR_EXTI_PIN);

    exti.EXTI_Line    = EXTI_Line11;
    exti.EXTI_Mode    = EXTI_Mode_Interrupt;
    exti.EXTI_Trigger = EXTI_Trigger_Falling;   /* NEC 每个码元以下降沿开头 */
    exti.EXTI_LineCmd = ENABLE;
    EXTI_Init(&exti);

    /* 抢占 3：低于 TIM2(抢占2) 的呼吸灯 PWM，不干扰已有功能 */
    nvic.NVIC_IRQChannel                   = EXTI15_10_IRQn;
    nvic.NVIC_IRQChannelPreemptionPriority = 3;
    nvic.NVIC_IRQChannelSubPriority        = 1;
    nvic.NVIC_IRQChannelCmd                = ENABLE;
    NVIC_Init(&nvic);

    /* TIM4: 1MHz 自由计数（hcsr04_drv 也配一次，幂等无害） */
    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM4, ENABLE);
    tim.TIM_Prescaler     = 72u - 1u;
    tim.TIM_Period        = 0xFFFFu;
    tim.TIM_ClockDivision = TIM_CKD_DIV1;
    tim.TIM_CounterMode   = TIM_CounterMode_Up;
    TIM_TimeBaseInit(TIM4, &tim);
    TIM_SetCounter(TIM4, 0u);
    TIM_Cmd(TIM4, ENABLE);

    s_lastFallUs = (uint16_t)TIM_GetCounter(TIM4);
    s_bitCnt     = 0u;
    s_frameReady = 0u;
    s_repeatCnt  = 0u;
}

void EXTI15_10_IRQHandler(void)
{
    uint16_t now;
    uint16_t dt;

    if (EXTI_GetITStatus(EXTI_Line11) != RESET)
    {
        now = (uint16_t)TIM_GetCounter(TIM4);
        dt  = (uint16_t)(now - s_lastFallUs);
        s_lastFallUs = now;

        if ((dt >= NEC_US_LEAD_LO) && (dt <= NEC_US_LEAD_HI))
        {
            s_bitCnt = 0u;              /* 引导码，开始收 32 位 */
            s_shift  = 0u;
        }
        else if ((dt >= NEC_US_RPT_LO) && (dt <= NEC_US_RPT_HI))
        {
            if (s_repeatCnt < 255u)     /* 按住不放的重复帧 */
            {
                s_repeatCnt++;
            }
        }
        else if ((dt >= NEC_US_B0_LO) && (dt <= NEC_US_B0_HI))
        {
            s_shift = s_shift << 1;     /* bit 0 */
            s_bitCnt++;
        }
        else if ((dt >= NEC_US_B1_LO) && (dt <= NEC_US_B1_HI))
        {
            s_shift = (s_shift << 1) | 1u;  /* bit 1 */
            s_bitCnt++;
        }
        else
        {
            s_bitCnt = 0u;              /* 空闲后首个下降沿/干扰 -> 复位 */
        }

        if (s_bitCnt >= 32u)
        {
            s_frame      = s_shift;
            s_frameReady = 1u;
            s_bitCnt     = 0u;
        }

        EXTI_ClearITPendingBit(EXTI_Line11);
    }
}

uint8_t NecIr_GetRaw(uint32_t *raw)
{
    uint8_t ok;

    __disable_irq();
    ok           = s_frameReady;
    s_frameReady = 0u;
    if (ok != 0u)
    {
        *raw = s_frame;
    }
    __enable_irq();

    return ok;
}

uint8_t NecIr_TakeRepeatCount(void)
{
    uint8_t n;

    __disable_irq();
    n           = s_repeatCnt;
    s_repeatCnt = 0u;
    __enable_irq();

    return n;
}

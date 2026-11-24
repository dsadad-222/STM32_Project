/**
  ******************************************************************************
  * @file    Drv_Common/pwm_drv.c
  * @brief   软件 PWM 呼吸灯实现（TIM2 20kHz 定时中断 + PG14 位翻转）
  *
  *          中断里做三件事：
  *              1. 计数器 s_pwmCnt 在 0~99 之间循环（一个 PWM 周期）
  *              2. s_pwmCnt < 占空比 -> 拉高 PG14，否则拉低
  *              3. 只在电平真正变化时才写 GPIO，省掉无谓的总线操作
  ******************************************************************************
  */

#include "pwm_drv.h"
#include "led_drv.h"
#include "systick_drv.h"

static volatile uint8_t s_pwmCnt  = 0u;     /* PWM 周期内的计数值 0~99 */
static volatile uint8_t s_duty    = 0u;     /* 当前占空比 0~100 */
static volatile uint8_t s_active  = 0u;     /* 1 = 正在呼吸 */
static uint8_t          s_level   = 0u;     /* 亮度等级 0~100（主循环调整）*/
static uint8_t          s_dirUp   = 1u;     /* 1 = 变亮，0 = 变暗 */
static uint32_t         s_lastStepMs = 0u;
static volatile uint8_t s_rgbMask = 0u;     /* 呼吸时同步驱动的 RGB 位掩码（0=不驱动）*/

/* 直接写，不做"电平没变就跳过"的缓存：主循环里的 LED_On/Off 不经过这里，
 * 一旦做缓存，两边状态会失同步（例如 L1 把灯点亮后缓存仍记着"灭"，
 * 进入呼吸时第一格"灭"会被跳过，灯就卡在常亮），这种 bug 排查起来极其费劲。
 * 20kHz 写一次 ODR 的开销完全可以接受。 */
static void Led1Drive(uint8_t on)
{
    if (on != 0u)
    {
        LED_On(LED1);
    }
    else
    {
        LED_Off(LED1);
    }
}

void Breath_Init(void)
{
    TIM_TimeBaseInitTypeDef tim;
    NVIC_InitTypeDef        nvic;
    uint16_t                period;

    RCC_APB1PeriphClockCmd(RCC_APB1Periph_TIM2, ENABLE);

    /* TIM2 时钟 = 72MHz（APB1 36MHz，定时器时钟 ×2），20kHz 中断 */
    period = (uint16_t)((PWM_TIMER_CLK / PWM_TICK_HZ) - 1u);

    tim.TIM_Prescaler         = 0;
    tim.TIM_Period            = period;
    tim.TIM_ClockDivision     = TIM_CKD_DIV1;
    tim.TIM_CounterMode       = TIM_CounterMode_Up;
    tim.TIM_RepetitionCounter = 0;
    TIM_TimeBaseInit(TIM2, &tim);

    TIM_ClearITPendingBit(TIM2, TIM_IT_Update);
    TIM_ITConfig(TIM2, TIM_IT_Update, ENABLE);

    /* 优先级给得比 SysTick 低一档即可，避免打断系统时基 */
    nvic.NVIC_IRQChannel                   = TIM2_IRQn;
    nvic.NVIC_IRQChannelPreemptionPriority = 2;
    nvic.NVIC_IRQChannelSubPriority        = 0;
    nvic.NVIC_IRQChannelCmd                = ENABLE;
    NVIC_Init(&nvic);

    s_pwmCnt = 0u;
    s_duty   = 0u;
    s_active = 0u;
}

void Breath_Start(void)
{
    s_active     = 1u;
    s_level      = 0u;
    s_dirUp      = 1u;
    s_pwmCnt     = 0u;
    s_duty       = 0u;
    s_lastStepMs = Get_SysRunTime();

    /* 板上那颗大灯（左上角，左右转向灯里的"左"）挂在 RGB 三色上，
     * 让它和 PG14 一起呼吸。
     * ⚠ 只用【红色通道 PG1】——任务书需求2 要求"左转向灯（红色）呼吸"。
     *   用 RGB_PIN_MASK(PG1|PG2) 会变成红+蓝 = 紫色，与任务书不符。 */
    s_rgbMask = RGB_BREATH_PIN_MASK;

    LED_Off(LED1);                              /* 从"全暗"起步 */
    GPIO_ResetBits(RGB_GPIO_PORT, RGB_BREATH_PIN_MASK);
    TIM_Cmd(TIM2, ENABLE);                      /* 打开定时中断，开始出波形 */
}

void Breath_Stop(void)
{
    s_active  = 0u;
    s_duty    = 0u;
    s_level   = 0u;
    s_rgbMask = 0u;

    TIM_Cmd(TIM2, DISABLE);     /* 关掉定时器，停止中断 */
    TIM_ClearITPendingBit(TIM2, TIM_IT_Update);

    LED_Off(LED1);
    GPIO_ResetBits(RGB_GPIO_PORT, RGB_BREATH_PIN_MASK);   /* 呼吸通道交回主循环管理 */
}

uint8_t Breath_IsActive(void)
{
    return s_active;
}

/* 诊断用：当前占空比与 PWM 计数值（0~99）。
 * 日志里 duty 在 0~100 来回走 = 软件正常；cnt 在动 = 中断正常 */
uint8_t Breath_GetDuty(void)
{
    return s_duty;
}

uint8_t Breath_GetPwmCnt(void)
{
    return s_pwmCnt;
}

/* 主循环调用：每 20ms 把亮度等级走一格，形成"渐亮—渐暗"的呼吸曲线 */
void Breath_Service(void)
{
    uint32_t now;

    if (s_active == 0u)
    {
        return;
    }

    now = Get_SysRunTime();
    if ((uint32_t)(now - s_lastStepMs) < BREATH_STEP_MS)
    {
        return;
    }
    s_lastStepMs = now;

    if (s_dirUp != 0u)
    {
        if ((uint16_t)s_level + BREATH_STEP_LEVEL >= PWM_LEVEL_MAX)
        {
            s_level = (uint8_t)PWM_LEVEL_MAX;
            s_dirUp = 0u;
        }
        else
        {
            s_level = (uint8_t)(s_level + BREATH_STEP_LEVEL);
        }
    }
    else
    {
        if (s_level <= BREATH_STEP_LEVEL)
        {
            s_level = 0u;
            s_dirUp = 1u;
        }
        else
        {
            s_level = (uint8_t)(s_level - BREATH_STEP_LEVEL);
        }
    }

    s_duty = s_level;
}

/* TIM2 更新中断：软件 PWM 的核心，20kHz 执行一次 */
void TIM2_IRQHandler(void)
{
    uint8_t on;
    uint8_t mask;

    if (TIM_GetITStatus(TIM2, TIM_IT_Update) != RESET)
    {
        TIM_ClearITPendingBit(TIM2, TIM_IT_Update);

        s_pwmCnt++;
        if (s_pwmCnt >= PWM_LEVEL_MAX)
        {
            s_pwmCnt = 0u;
        }

        on = ((s_active != 0u) && (s_pwmCnt < s_duty)) ? 1u : 0u;
        Led1Drive(on);

        /* 同步驱动左灯珠 TLED 的【红色通道 PG1】，让它一起呼吸。
           任务书需求2 要求"左转向灯（红色）呼吸"，所以只走红色，不加蓝色
           （红+蓝 会变成紫色，2026-09-18 实测踩过）。
           ⚠ 绿色通道在 PE7（GPIOE），单端口掩码表达不了，不参与呼吸。
           用 BSRR 直接置位/复位，只写一次寄存器。 */
        mask = s_rgbMask;
        if (mask != 0u)
        {
            if (on != 0u)
            {
                GPIO_SetBits(RGB_GPIO_PORT, mask);
            }
            else
            {
                GPIO_ResetBits(RGB_GPIO_PORT, mask);
            }
        }
    }
}

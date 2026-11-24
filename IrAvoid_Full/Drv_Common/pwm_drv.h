/**
  ******************************************************************************
  * @file    Drv_Common/pwm_drv.h
  * @brief   左转向灯（LED1 / PG14）呼吸灯：TIM2 定时中断 + 软件 PWM
  *
  *          一、为什么用"软件 PWM"？
  *              STM32F103 的硬件 PWM 要求引脚本身带定时器复用功能（TIMx_CHx）。
  *              但板子上的左转向灯接的是 PG14，查数据手册：PG14 的复用功能是
  *              FSMC_A25（外部总线地址线），**没有任何定时器通道**，所以没法用
  *              TIM_OCxInit 直接在 PG14 出硬件 PWM。
  *              解决办法：用 TIM2 产生一个高频定时中断当"时间基准"，在中断里
  *              自己数数、自己翻转 PG14，等效出一个 PWM 波——这就是软件 PWM。
  *
  *          二、参数怎么定的
  *              TIM2 挂在 APB1（36MHz），APB1 分频系数不为 1 时定时器时钟 ×2 = 72MHz。
  *              取 20kHz 中断：ARR = 72 000 000 / 20 000 - 1 = 3599。
  *              一个 PWM 周期分成 100 级（0~100）：
  *                  PWM 频率 = 20kHz / 100 = 200Hz  > 100Hz，肉眼看不到闪烁。
  *              占空比每 20ms 调 2 级：半程 1s，一亮一暗一个来回 2s，呼吸感自然。
  *
  *          三、中断开销
  *              20kHz 中断在 72MHz 主频下大约占 3% 的 CPU，只在改引脚电平的时候
  *              才写 GPIO，退出呼吸模式会把 TIM2 关掉，不留额外负担。
  ******************************************************************************
  */

#ifndef __PWM_DRV_H
#define __PWM_DRV_H

#include "stm32f10x.h"

#define PWM_TIMER_CLK       72000000u   /* TIM2 时钟：APB1 36MHz，定时器倍频 ×2 */
#define PWM_TICK_HZ         20000u      /* TIM2 中断频率（Hz）*/
#define PWM_LEVEL_MAX       100u        /* 一个 PWM 周期分 100 级 */
#define PWM_FREQ_HZ         (PWM_TICK_HZ / PWM_LEVEL_MAX)   /* 200Hz */

#define BREATH_STEP_MS      20u         /* 每 20ms 调整一次亮度 */
#define BREATH_STEP_LEVEL   2u          /* 每次调 2 级（半程 1s，来回 2s）*/

void    Breath_Init(void);              /* 初始化 TIM2（不启动呼吸）*/
void    Breath_Start(void);             /* 开始呼吸（KEY2 按下 -> 亮）*/
void    Breath_Stop(void);              /* 停止呼吸，灯灭 */
uint8_t Breath_IsActive(void);          /* 1 = 正在呼吸（此时主循环不要动 LED1）*/
void    Breath_Service(void);           /* 主循环调用：按 20ms 节奏调占空比 */
uint8_t Breath_GetDuty(void);           /* 诊断：当前占空比 0~100 */
uint8_t Breath_GetPwmCnt(void);         /* 诊断：PWM 周期内计数值 0~99 */

#endif /* __PWM_DRV_H */

#ifndef __NEC_IR_DRV_H
#define __NEC_IR_DRV_H

#include "stm32f10x.h"

/*
 * NEC 红外遥控接收驱动（板载 U5 HS0038B，输出脚 -> PG11）
 * HS0038B 空闲输出高，收到 38kHz 载波时拉低。
 * NEC 时序（以下降沿间隔计）：
 *   引导码   13.5ms (9ms 低 + 4.5ms 高)
 *   重复码   11.25ms (9ms 低 + 2.25ms 高)
 *   bit=0    1.12ms
 *   bit=1    2.25ms
 * 帧格式 32 位: 地址8 + 地址反码8 + 命令8 + 命令反码8
 * 计时用 TIM4(1MHz)，中断用 EXTI11（抢占 3，低于 TIM2 的 2）。
 */

void    NecIr_Init(void);
/* 取一帧原始 32 位码。返回 1=收到新帧(读完清零) 0=无 */
uint8_t NecIr_GetRaw(uint32_t *raw);
/* 自增的重复码计数（按住不放时），读了清零 */
uint8_t NecIr_TakeRepeatCount(void);

#endif /* __NEC_IR_DRV_H */

#ifndef __HC_SR04_DRV_H
#define __HC_SR04_DRV_H

#include "stm32f10x.h"

/*
 * HC-SR04 超声波测距驱动（板上 J1 座，丝印 Ultrasonic）
 *   J1.1 = 5V   J1.2 = TRIG -> PF11 (推挽输出, FT 脚)
 *   J1.3 = ECHO -> PF12 (浮空输入, FT 脚 5V 容忍)
 *   J1.4 = GND
 * 计时用 TIM4（1MHz, 1us 分辨率, 与呼吸灯 TIM2 互不干扰）。
 */

/* 上次测量的失败原因（诊断用，插错线时能一眼看出卡在哪一步）*/
#define HCSR04_ERR_NONE        0u   /* 成功 */
#define HCSR04_ERR_NO_UP       1u   /* ECHO 始终没拉高：模块没响应（供电/接线/模块坏）*/
#define HCSR04_ERR_STUCK_HIGH  2u   /* ECHO 一直是高：接线短路或模块卡死 */
#define HCSR04_ERR_RANGE       3u   /* 有回波但脉宽超出 2cm~4m 量程 */
#define HCSR04_ERR_SHORT       4u   /* ECHO 有拉高但脉宽 < 116us（太近/自激）*/

void     Hcsr04_Init(void);
/* 单次测量，返回距离 mm；0xFFFF = 超时/无回波/超量程 */
uint16_t Hcsr04_GetDistanceMm(void);
/* 连测 3 次取中值，抗单次抖动 */
uint16_t Hcsr04_GetDistanceMid3(void);
/* 上次测量的失败码（HCSR04_ERR_xxx）*/
uint8_t  Hcsr04_GetLastErr(void);
/* 上次测量到的 ECHO 高电平宽度(us)，0 = 没测到，0xFFFF = 一直高 */
uint16_t Hcsr04_GetLastRawUs(void);
/* ECHO 引脚当前电平（1 = 高）*/
uint8_t  Hcsr04_EchoLevel(void);

#endif /* __HC_SR04_DRV_H */

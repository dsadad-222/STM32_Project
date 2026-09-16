/**
  ******************************************************************************
  * @file    Drv_Common/beep_drv.h
  * @brief   蜂鸣器驱动（PG12）
  *          板上为 5V 有源蜂鸣器，经 SS8050 三极管驱动，
  *          引脚输出高电平 -> 三极管导通 -> 蜂鸣器鸣叫
  ******************************************************************************
  */

#ifndef __BEEP_DRV_H
#define __BEEP_DRV_H

#include "stm32f10x.h"

void Beep_Init(void);
void Beep_On(void);
void Beep_Off(void);
void Beep_Beep(uint16_t ms);

#endif /* __BEEP_DRV_H */

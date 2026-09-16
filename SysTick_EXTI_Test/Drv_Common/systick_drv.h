/**
  ******************************************************************************
  * @file    Drv_Common/systick_drv.h
  * @author  陈相林 (智能3班)
  * @brief   SysTick 驱动：提供 1ms 时基与系统运行时间
  ******************************************************************************
  */

#ifndef __SYSTICK_DRV_H
#define __SYSTICK_DRV_H

#include <stdint.h>

void SysTick_Init(void);
uint64_t Get_SysRunTime(void);

#endif /* __SYSTICK_DRV_H */

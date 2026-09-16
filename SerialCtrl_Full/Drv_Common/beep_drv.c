/**
  ******************************************************************************
  * @file    Drv_Common/beep_drv.c
  * @brief   蜂鸣器驱动实现（PG12，高电平鸣叫）
  ******************************************************************************
  */

#include "beep_drv.h"
#include "systick_drv.h"

#define BEEP_PORT     GPIOG
#define BEEP_PIN      GPIO_Pin_12

void Beep_Init(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG, ENABLE);

    GPIO_InitStructure.GPIO_Pin   = BEEP_PIN;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(BEEP_PORT, &GPIO_InitStructure);

    /* 上电默认不响 */
    GPIO_ResetBits(BEEP_PORT, BEEP_PIN);
}

void Beep_On(void)
{
    GPIO_SetBits(BEEP_PORT, BEEP_PIN);
}

void Beep_Off(void)
{
    GPIO_ResetBits(BEEP_PORT, BEEP_PIN);
}

/* 阻塞式响一声，仅用于上电提示等场景 */
void Beep_Beep(uint16_t ms)
{
    Beep_On();
    DelayMs(ms);
    Beep_Off();
}

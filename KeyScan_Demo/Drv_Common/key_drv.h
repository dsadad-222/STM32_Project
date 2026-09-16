/**
  ******************************************************************************
  * @file    Drv_Common/key_drv.h
  * @brief   按键扫描驱动：短按/长按/单击/双击识别
  *          - KEY 按下为低电平（外部上拉）
  *          - 消抖 20ms、短按/长按阈值 1000ms、双击间隔 300ms
  *          - 主循环每 10~20ms 调用 Key_Scan 一次
  ******************************************************************************
  */

#ifndef __KEY_DRV_H
#define __KEY_DRV_H

#include <stdint.h>
#include "stm32f10x.h"

/* 按键时序参数（毫秒） */
#define KEY_DEBOUNCE_MS         20      /* 消抖时间 */
#define KEY_SHORT_LONG_MS       1000    /* 短按/长按分界 */
#define KEY_DOUBLE_CLICK_MS     300     /* 双击间隔阈值 */

typedef enum
{
    KEY_EVT_NONE = 0,
    KEY_EVT_CLICK,            /* 短按（单击） */
    KEY_EVT_DOUBLE_CLICK,     /* 双击 */
    KEY_EVT_LONG_HOLD_START,  /* 长按开始（持续按下 >= 1s） */
    KEY_EVT_LONG_HOLD_END,    /* 长按结束（释放） */
} KeyEvent;

typedef enum
{
    KS_IDLE = 0,
    KS_DEBOUNCE_DOWN,         /* 消抖中（按下） */
    KS_PRESSED,               /* 已确认按下 */
    KS_CLICK_PENDING,         /* 短按释放，等待第二次点击 */
    KS_DOUBLE_CLICK,          /* 已确认双击 */
    KS_LONG_HOLD,             /* 长按保持 */
} KeyState;

typedef struct
{
    GPIO_TypeDef* port;       /* GPIO 端口 */
    uint16_t pin;             /* GPIO 引脚 */
    uint8_t pressedLevel;     /* 按下时的电平：Bit_RESET=低，Bit_SET=高 */

    uint8_t rawLevel;         /* 当前原始电平（消抖前） */
    uint8_t stableLevel;      /* 消抖后的稳定电平 */
    uint8_t prevLevel;        /* 上一次稳定电平（用于边沿检测） */
    uint32_t rawChangeMs;     /* 上次原始电平变化的时刻 */

    KeyState state;           /* 当前状态机状态 */
    uint32_t pressStartMs;    /* 按下时刻 */
    uint32_t releaseMs;       /* 释放时刻 */
    uint8_t longHoldActive;   /* 长按中标记（LED 常亮用） */

    KeyEvent event;           /* 待读取事件 */
} Key_t;

void Key_Init(Key_t* key, GPIO_TypeDef* port, uint16_t pin, uint8_t pressedLevel);
void Key_Scan(Key_t* key);
KeyEvent Key_GetEvent(Key_t* key);
uint8_t  Key_IsLongHold(Key_t* key);

#endif /* __KEY_DRV_H */

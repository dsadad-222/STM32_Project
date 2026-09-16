/**
  ******************************************************************************
  * @file    Drv_Common/key_drv.h
  * @brief   板载功能按键驱动（KEY1/KEY2/KEY3）
  *
  *          板上三个按键都是"一端接地、一端接 IO"，IO 平时被 10K 电阻上拉到 3V3，
  *          所以按下 = 低电平。配置成上拉输入，主循环每 10ms 调一次 Key_Scan：
  *              按下沿 -> 消抖 20ms -> 确认按下 -> 立即返回一次单击事件
  *          只做"单击"识别（本任务按键只用来切换功能，不需要双击/长按）。
  ******************************************************************************
  */

#ifndef __KEY_DRV_H
#define __KEY_DRV_H

#include "stm32f10x.h"

#define KEY_PORT            GPIOG
#define KEY_GPIO_CLK        RCC_APB2Periph_GPIOG

#define KEY1_PIN            GPIO_Pin_3      /* PG3 */
#define KEY2_PIN            GPIO_Pin_4      /* PG4 —— 本任务：按下切换左转向灯呼吸灯 */
#define KEY3_PIN            GPIO_Pin_5      /* PG5 */

#define KEY_DEBOUNCE_MS     20u             /* 消抖时间（ms）*/
#define KEY_SCAN_PERIOD_MS  10u             /* 建议扫描周期（ms）*/

typedef enum
{
    KEY_EVT_NONE = 0,
    KEY_EVT_KEY1_CLICK,     /* 切换 OLED 显示页（温度数据页 / 文本页）*/
    KEY_EVT_KEY2_CLICK,     /* 左转向灯呼吸灯 开/关 */
    KEY_EVT_KEY3_CLICK      /* 立即采样一次温度并上报 */
} KeyEvent;

void      Key_Init(void);
KeyEvent  Key_Scan(void);       /* 每 10ms 调用一次，无事件返回 KEY_EVT_NONE */

#endif /* __KEY_DRV_H */

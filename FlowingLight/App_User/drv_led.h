#ifndef __DRV_LED_H__
#define __DRV_LED_H__

#include <stdint.h>

/* LED 编号 (与 chapter4 流水灯架构一致)
 *   LED1/LED2    : 板载两个独立 LED
 *   LRGB_R/G/B   : 左侧 RGB 灯 (红/绿/蓝)
 *   RRGB_R/G/B   : 右侧 RGB 灯 (红/绿/蓝)
 */
typedef enum {
    LED1   = 0,
    LED2,
    LRGB_R,
    LRGB_G,
    LRGB_B,
    RRGB_R,
    RRGB_G,
    RRGB_B
} LED_NO_t;

/* 驱动初始化: 开时钟 + 配 8 个引脚为推挽输出 */
void Led_Drv_Init(void);

/* 点亮指定 LED */
void Led_On(LED_NO_t ledno);

/* 熄灭指定 LED */
void Led_Off(LED_NO_t ledno);

/* 翻转指定 LED 当前状态 */
void Led_Toggle(LED_NO_t ledno);

#endif

/**
 * 任务3：寄存器方式控制按键
 * 平台：STM32F103ZET6（秉火/野火类开发板）
 * 说明：不使用标准库函数，直接操作寄存器。按键按下时引脚被拉低（IDR 读 0）则点亮对应 LED。
 *       LED1=PG14，LED2=PG15（高电平点亮）
 *       KEY1=PG3，KEY2=PG4，KEY3=PG5（开发板按下=低电平）
 *       扩展：KEY1 控制 LED1，KEY2 控制 LED2，KEY3 同时点亮两个指示灯。
 */
#include "stm32f10x.h"

int main(void)
{
    /* 1. 开启 GPIOG 时钟：RCC_APB2ENR 第 8 位 */
    RCC->APB2ENR |= (uint32_t)(1u << 8);

    /* 2. 配置 PG14 / PG15 为推挽输出 50MHz（CRH） */
    GPIOG->CRH &= ~((uint32_t)0x0F << 24);
    GPIOG->CRH |=  ((uint32_t)0x03 << 24);   /* PG14 */
    GPIOG->CRH &= ~((uint32_t)0x0F << 28);
    GPIOG->CRH |=  ((uint32_t)0x03 << 28);   /* PG15 */

    /* 3. 配置 PG3 / PG4 / PG5 为浮空输入（CRL）
     *    CNF[1:0]=01(浮空) MODE[1:0]=00(输入) => 0x4
     *    PG3 在 CRL[15:12]，PG4 在 CRL[19:16]，PG5 在 CRL[23:20] */
    GPIOG->CRL &= ~((uint32_t)0x0F << 12);
    GPIOG->CRL |=  ((uint32_t)0x04 << 12);   /* PG3 */
    GPIOG->CRL &= ~((uint32_t)0x0F << 16);
    GPIOG->CRL |=  ((uint32_t)0x04 << 16);   /* PG4 */
    GPIOG->CRL &= ~((uint32_t)0x0F << 20);
    GPIOG->CRL |=  ((uint32_t)0x04 << 20);   /* PG5 */

    /* 4. 主循环：按键扫描 -> 控制 LED */
    while (1)
    {
        uint32_t idr  = GPIOG->IDR;
        uint32_t set  = 0u;
        uint32_t clr  = (uint32_t)((1u << 14) | (1u << 15)); /* 默认都熄灭 */

        /* KEY1(PG3) 按下 -> LED1(PG14) 亮 */
        if ((idr & (1u << 3)) == 0u)
            set |= (uint32_t)(1u << 14);

        /* KEY2(PG4) 按下 -> LED2(PG15) 亮 */
        if ((idr & (1u << 4)) == 0u)
            set |= (uint32_t)(1u << 15);

        /* KEY3(PG5) 按下 -> LED1+LED2 都亮（扩展两个指示灯） */
        if ((idr & (1u << 5)) == 0u)
            set |= (uint32_t)((1u << 14) | (1u << 15));

        clr &= ~set;                          /* 已置位的灯不进清除列表 */

        GPIOG->BSRR = set;                    /* 置位 */
        GPIOG->BRR  = clr;                    /* 清位 */
    }
}

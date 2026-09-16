/**
 * 任务2：寄存器方式控制 IO 点亮 LED
 * 平台：STM32F103ZET6（秉火/野火类开发板）
 * 说明：不使用标准库函数，直接操作寄存器地址（见参考手册 GPIO/RCC 章节）。
 *       LED1=PG14，LED2=PG15，高电平点亮（共阴接法）。
 */
#include "stm32f10x.h"

/* 软件延时：循环次数固定，主频越高闪得越快（本工程系统时钟 72M） */
static void delay(uint32_t n)
{
    for (volatile uint32_t i = 0; i < n; i++)
        ;
}

int main(void)
{
    /* 1. 开启 GPIOG 时钟：RCC_APB2ENR 第 8 位（IOPG EN） */
    RCC->APB2ENR |= (uint32_t)(1u << 8);

    /* 2. 配置 PG14 / PG15 为推挽输出 50MHz
     *    CRH 每 4 位控制一个引脚：CNF[1:0]=00(推挽) MODE[1:0]=11(50MHz) => 0x3
     *    PG14 在 CRH[27:24]，PG15 在 CRH[31:28] */
    GPIOG->CRH &= ~((uint32_t)0x0F << 24);   /* 清 PG14 */
    GPIOG->CRH |=  ((uint32_t)0x03 << 24);
    GPIOG->CRH &= ~((uint32_t)0x0F << 28);   /* 清 PG15 */
    GPIOG->CRH |=  ((uint32_t)0x03 << 28);

    /* 3. 主循环：两灯交替闪烁 */
    while (1)
    {
        /* 置位 PG14/PG15（BSRR 低 16 位写 1 置高）-> 亮 */
        GPIOG->BSRR = (uint32_t)((1u << 14) | (1u << 15));
        delay(0x3FFFFu);

        /* 清位 PG14/PG15（BRR 写 1 清低）-> 灭 */
        GPIOG->BRR = (uint32_t)((1u << 14) | (1u << 15));
        delay(0x3FFFFu);
    }
}

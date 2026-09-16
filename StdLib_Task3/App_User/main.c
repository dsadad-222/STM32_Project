/**
  ******************************************************************************
  * @file    App_User/main.c
  * @author  陈相林 (智能3班)
  * @brief   标准库版：任务2（按键控制 LED）+ RGB 灯组扩展
  *
  *  本工程在《chapter2.pdf》第7节"任务测试"的【任务2：基于标准库实现按键控制LED】
  *  基础上进行扩展：保留按键控制 LED 的原始功能，并额外点亮两组 RGB LED，
  *  支持任意颜色组合显示与闪烁。
  *
  *  引脚分配（依据 YB-DSF01-V1.0 原理图）：
  *    第一组 RGB LED(L1)：LRGB-R=PG0 / LRGB-G=PG1 / LRGB-B=PG2
  *    第二组 RGB LED(L2)：R=PE2 / G=PE3 / B=PE4
  *    基础 LED1=PG14  LED2=PG15   （高电平点亮）
  *    按键  KEY1=PG3  KEY2=PG4  KEY3=PG5   （浮空输入，外接上拉按下为高）
  *
  *  功能：
  *    【任务2 原始功能】KEY1(PG3) 按下 -> LED1(PG14) 点亮；松开 -> 熄灭
  *    【扩展功能】
  *      - 两组 RGB LED 可显示 8 种颜色组合：全灭/红/绿/蓝/黄/紫/青/白
  *      - KEY2(PG4)：切换 RGB 颜色组合（8 档循环）
  *      - KEY3(PG5)：切换 RGB 显示模式（0=静态 / 1=整体闪烁 / 2=两组交替闪）
  *      - 任意颜色组合可显示；可单独控制哪些颜色亮、哪些不亮
  *      - 闪烁模式下 LED2(PG15) 参与指示（与 LED1 反相）
  ******************************************************************************
  */

#include "stm32f10x.h"

/* ---------------------- 软件延时 ---------------------- */
static void Delay(__IO uint32_t nCount)
{
    for (; nCount != 0; nCount--);
}

/* ---------------------- RGB 颜色状态 ---------------------- */
typedef struct {
    uint8_t r;
    uint8_t g;
    uint8_t b;
} RGB_Color_t;

typedef struct {
    RGB_Color_t rgb1;   /* 第一组 RGB (PG0/PG1/PG2) */
    RGB_Color_t rgb2;   /* 第二组 RGB (PE2/PE3/PE4) */
} RGB_State_t;

/* 8 种颜色组合（共阴 RGB：1=点亮，0=熄灭） */
static const RGB_State_t color_table[8] = {
    /*  rgb1(r,g,b)   rgb2(r,g,b) */
    { {0, 0, 0}, {0, 0, 0} },  /* 0 - 全灭 */
    { {1, 0, 0}, {1, 0, 0} },  /* 1 - 红 */
    { {0, 1, 0}, {0, 1, 0} },  /* 2 - 绿 */
    { {0, 0, 1}, {0, 0, 1} },  /* 3 - 蓝 */
    { {1, 1, 0}, {1, 1, 0} },  /* 4 - 黄（红+绿） */
    { {1, 0, 1}, {1, 0, 1} },  /* 5 - 紫（红+蓝） */
    { {0, 1, 1}, {0, 1, 1} },  /* 6 - 青（绿+蓝） */
    { {1, 1, 1}, {1, 1, 1} },  /* 7 - 白（红+绿+蓝） */
};

/* ---------------------- GPIO 配置 ---------------------- */
static void GPIO_Config(void)
{
    GPIO_InitTypeDef GPIO_InitStructure;

    /* 1. 开 GPIOG / GPIOE 时钟 */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG | RCC_APB2Periph_GPIOE, ENABLE);

    /* 2. RGB1 (PG0/PG1/PG2) 推挽输出 */
    GPIO_InitStructure.GPIO_Pin  = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_Out_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOG, &GPIO_InitStructure);

    /* 3. RGB2 (PE2/PE3/PE4) 推挽输出 */
    GPIO_InitStructure.GPIO_Pin  = GPIO_Pin_2 | GPIO_Pin_3 | GPIO_Pin_4;
    GPIO_Init(GPIOE, &GPIO_InitStructure);

    /* 4. LED1 (PG14) / LED2 (PG15) 推挽输出 */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_14 | GPIO_Pin_15;
    GPIO_Init(GPIOG, &GPIO_InitStructure);

    /* 5. KEY1/2/3 (PG3/PG4/PG5) 浮空输入（板载有上拉/下拉电阻） */
    GPIO_InitStructure.GPIO_Pin = GPIO_Pin_3 | GPIO_Pin_4 | GPIO_Pin_5;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOG, &GPIO_InitStructure);

    /* 6. 默认全灭 */
    GPIO_ResetBits(GPIOG, GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2 |
                             GPIO_Pin_14 | GPIO_Pin_15);
    GPIO_ResetBits(GPIOE, GPIO_Pin_2 | GPIO_Pin_3 | GPIO_Pin_4);
}

/* ---------------------- RGB 应用到硬件 ---------------------- */
/* 共阴 RGB：高电平点亮（根据原理图，共阴接 GND，IO 高电平点亮） */
static void RGB_Apply(const RGB_State_t *s)
{
    /* RGB1: PG0=R, PG1=G, PG2=B */
    if (s->rgb1.r) GPIO_SetBits(GPIOG, GPIO_Pin_0); else GPIO_ResetBits(GPIOG, GPIO_Pin_0);
    if (s->rgb1.g) GPIO_SetBits(GPIOG, GPIO_Pin_1); else GPIO_ResetBits(GPIOG, GPIO_Pin_1);
    if (s->rgb1.b) GPIO_SetBits(GPIOG, GPIO_Pin_2); else GPIO_ResetBits(GPIOG, GPIO_Pin_2);
    /* RGB2: PE2=R, PE3=G, PE4=B */
    if (s->rgb2.r) GPIO_SetBits(GPIOE, GPIO_Pin_2); else GPIO_ResetBits(GPIOE, GPIO_Pin_2);
    if (s->rgb2.g) GPIO_SetBits(GPIOE, GPIO_Pin_3); else GPIO_ResetBits(GPIOE, GPIO_Pin_3);
    if (s->rgb2.b) GPIO_SetBits(GPIOE, GPIO_Pin_4); else GPIO_ResetBits(GPIOE, GPIO_Pin_4);
}

/* 全灭（用于闪烁暗相） */
static void RGB_AllOff(void)
{
    GPIO_ResetBits(GPIOG, GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2);
    GPIO_ResetBits(GPIOE, GPIO_Pin_2 | GPIO_Pin_3 | GPIO_Pin_4);
}

/* ---------------------- 按键边沿检测（带简单消抖） ---------------------- */
/* 返回：1=检测到一次完整按下并释放（用于 KEY2/KEY3 切档），0=无动作 */
static uint8_t Key_Toggle(GPIO_TypeDef* port, uint16_t pin)
{
    if (GPIO_ReadInputDataBit(port, pin) == Bit_SET)
    {
        Delay(0xFFFF);   /* 消抖 */
        if (GPIO_ReadInputDataBit(port, pin) == Bit_SET)
        {
            while (GPIO_ReadInputDataBit(port, pin) == Bit_SET);  /* 等待释放 */
            return 1;
        }
    }
    return 0;
}

/* ---------------------- 主函数 ---------------------- */
int main(void)
{
    uint8_t color_idx = 0;          /* 当前 RGB 颜色 0..7 */
    uint8_t mode      = 0;          /* 0=静态 / 1=整体闪烁 / 2=两组交替闪 */
    uint32_t tick     = 0;          /* 时间片计数器 */
    uint8_t blink_on  = 0;          /* 当前闪烁相位 */

    GPIO_Config();

    while (1)
    {
        /* ===== 【任务2 原始功能】KEY1(PG3) 实时控制 LED1(PG14) ===== */
        if (GPIO_ReadInputDataBit(GPIOG, GPIO_Pin_3) == Bit_SET)
            GPIO_SetBits(GPIOG, GPIO_Pin_14);     /* 按下 -> 点亮 LED1 */
        else
            GPIO_ResetBits(GPIOG, GPIO_Pin_14);   /* 松开 -> 熄灭 LED1 */

        /* ===== 【扩展】KEY2(PG4) 切 RGB 颜色组合 ===== */
        if (Key_Toggle(GPIOG, GPIO_Pin_4))
            color_idx = (color_idx + 1) % 8;

        /* ===== 【扩展】KEY3(PG5) 切 RGB 显示模式 ===== */
        if (Key_Toggle(GPIOG, GPIO_Pin_5))
            mode = (mode + 1) % 3;

        /* ===== 计算本帧 RGB 状态 ===== */
        RGB_State_t s = color_table[color_idx];

        /* ===== 根据模式刷新硬件 ===== */
        blink_on = (tick / 30) % 2;

        if (mode == 0)
        {
            /* 静态：颜色常亮，LED2 熄灭 */
            RGB_Apply(&s);
            GPIO_ResetBits(GPIOG, GPIO_Pin_15);
        }
        else if (mode == 1)
        {
            /* 整体闪烁：两组 RGB 同步亮灭，LED2 与 LED1 反相指示 */
            if (blink_on) {
                RGB_Apply(&s);
                GPIO_SetBits(GPIOG, GPIO_Pin_15);
            } else {
                RGB_AllOff();
                GPIO_ResetBits(GPIOG, GPIO_Pin_15);
            }
        }
        else  /* mode == 2 */
        {
            /* 两组交替闪：奇数拍 RGB1 亮 RGB2 灭；偶数拍相反 */
            if (blink_on)
            {
                RGB_Color_t saved = s.rgb2;
                s.rgb2 = (RGB_Color_t){0, 0, 0};
                RGB_Apply(&s);
                s.rgb2 = saved;
                GPIO_SetBits(GPIOG, GPIO_Pin_15);
            }
            else
            {
                RGB_Color_t saved = s.rgb1;
                s.rgb1 = (RGB_Color_t){0, 0, 0};
                RGB_Apply(&s);
                s.rgb1 = saved;
                GPIO_ResetBits(GPIOG, GPIO_Pin_15);
            }
        }

        /* 帧延时 */
        Delay(0x1FFFF);
        tick++;
    }
}

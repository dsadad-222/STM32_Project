/**
  ******************************************************************************
  * @file    Drv_Common/oled_drv.c
  * @brief   0.86 寸 OLED（SSD1306，128x32）驱动，软件 I2C1
  *
  *          写显存 -> OLED_Refresh() 把整屏 4 页一次性刷到屏上，
  *          避免每写一个字符就通信一次。
  ******************************************************************************
  */

#include "oled_drv.h"

/* ========================= 软件 I2C 底层 ========================= */

#define OLED_SCL_PIN        GPIO_Pin_6
#define OLED_SDA_PIN        GPIO_Pin_7
#define OLED_GPIO_PORT      GPIOB
#define OLED_GPIO_CLK       RCC_APB2Periph_GPIOB

#define SCL_HIGH()          GPIO_SetBits(OLED_GPIO_PORT, OLED_SCL_PIN)
#define SCL_LOW()           GPIO_ResetBits(OLED_GPIO_PORT, OLED_SCL_PIN)
#define SDA_HIGH()          GPIO_SetBits(OLED_GPIO_PORT, OLED_SDA_PIN)
#define SDA_LOW()           GPIO_ResetBits(OLED_GPIO_PORT, OLED_SDA_PIN)
#define SDA_READ()          GPIO_ReadInputDataBit(OLED_GPIO_PORT, OLED_SDA_PIN)

/* 软件模拟 I2C 的位延时。按 72MHz 主频估算，这里大约对应 100~200kHz。
   0.86 寸小屏线短，速度不敏感，留足余量保证稳定。 */
static void I2cDelay(void)
{
    volatile uint8_t wait = 12;
    while (wait != 0)
    {
        wait--;
    }
}

static void I2cStart(void)
{
    SDA_HIGH();
    SCL_HIGH();
    I2cDelay();
    SDA_LOW();          /* SCL 高电平期间 SDA 下降沿 = 起始条件 */
    I2cDelay();
    SCL_LOW();
    I2cDelay();
}

static void I2cStop(void)
{
    SDA_LOW();
    I2cDelay();
    SCL_HIGH();
    I2cDelay();
    SDA_HIGH();         /* SCL 高电平期间 SDA 上升沿 = 停止条件 */
    I2cDelay();
}

/* 发送一个字节，返回 0 表示从机给出了应答 */
static uint8_t I2cWriteByte(uint8_t byte)
{
    uint8_t i;
    uint8_t ackBit;

    for (i = 0; i < 8; i++)
    {
        if ((byte & 0x80) != 0)
        {
            SDA_HIGH();
        }
        else
        {
            SDA_LOW();
        }
        byte = (uint8_t)(byte << 1);
        I2cDelay();
        SCL_HIGH();     /* 时钟拉高期间数据有效 */
        I2cDelay();
        SCL_LOW();
        I2cDelay();
    }

    SDA_HIGH();         /* 释放 SDA，交给从机应答 */
    I2cDelay();
    SCL_HIGH();
    I2cDelay();
    ackBit = (uint8_t)SDA_READ();    /* 0 = 应答 */
    SCL_LOW();
    I2cDelay();

    return ackBit;
}

/* 控制字节：0x00 后面跟命令，0x40 后面跟显示数据 */
static void OledWriteCmd(uint8_t cmd)
{
    I2cStart();
    (void)I2cWriteByte(OLED_I2C_ADDR);
    (void)I2cWriteByte(0x00);
    (void)I2cWriteByte(cmd);
    I2cStop();
}

static void OledWriteData(const uint8_t *buf, uint16_t len)
{
    uint16_t i;

    I2cStart();
    (void)I2cWriteByte(OLED_I2C_ADDR);
    (void)I2cWriteByte(0x40);
    for (i = 0; i < len; i++)
    {
        (void)I2cWriteByte(buf[i]);
    }
    I2cStop();
}

/* ========================= 显存与字符 ========================= */

/* 整屏显存：4 页 x 128 列，每个字节代表该列上连续的 8 个像素 */
static uint8_t s_gram[OLED_PAGE_COUNT][OLED_WIDTH];

void OLED_Init(void)
{
    GPIO_InitTypeDef gpio;

    RCC_APB2PeriphClockCmd(OLED_GPIO_CLK, ENABLE);

    /* 开漏输出，配合板上 4.7K 上拉构成标准 I2C 总线 */
    gpio.GPIO_Pin   = OLED_SCL_PIN | OLED_SDA_PIN;
    gpio.GPIO_Mode  = GPIO_Mode_Out_OD;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(OLED_GPIO_PORT, &gpio);

    SCL_HIGH();
    SDA_HIGH();

    /* SSD1306 上电初始化序列（128x32 的复用比是 31，COM 配置是 0x02） */
    OledWriteCmd(0xAE);         /* 关显示 */
    OledWriteCmd(0xD5);         /* 时钟分频 */
    OledWriteCmd(0x80);
    OledWriteCmd(0xA8);         /* 复用比 = 32 行 */
    OledWriteCmd(0x1F);
    OledWriteCmd(0xD3);         /* 显示偏移 */
    OledWriteCmd(0x00);
    OledWriteCmd(0x40);         /* 起始行 = 0 */
    OledWriteCmd(0x8D);         /* 电荷泵 */
    OledWriteCmd(0x14);         /* 使能内部升压，模块只给 3.3V 时必须打开 */
    OledWriteCmd(0x20);         /* 页寻址模式 */
    OledWriteCmd(0x02);
    OledWriteCmd(0xA1);         /* 段重映射：列 127 映射到 SEG0 */
    OledWriteCmd(0xC8);         /* 行扫描方向反向 */
    OledWriteCmd(0xDA);         /* COM 引脚配置，128x32 用 0x02 */
    OledWriteCmd(0x02);
    OledWriteCmd(0x81);         /* 对比度 */
    OledWriteCmd(0x8F);
    OledWriteCmd(0xD9);         /* 预充电周期 */
    OledWriteCmd(0xF1);
    OledWriteCmd(0xDB);         /* VCOMH 取消选择电平 */
    OledWriteCmd(0x40);
    OledWriteCmd(0xA4);         /* 显示内容跟随显存 */
    OledWriteCmd(0xA6);         /* 正常显示（非反色）*/
    OledWriteCmd(0xAF);         /* 开显示 */

    OLED_Clear();
    OLED_Refresh();
}

void OLED_DisplayOn(void)
{
    OledWriteCmd(0xAF);
}

void OLED_DisplayOff(void)
{
    OledWriteCmd(0xAE);
}

void OLED_Clear(void)
{
    uint8_t page;
    uint8_t col;

    for (page = 0; page < OLED_PAGE_COUNT; page++)
    {
        for (col = 0; col < OLED_WIDTH; col++)
        {
            s_gram[page][col] = 0x00;
        }
    }
}

void OLED_ClearLine(uint8_t row)
{
    uint8_t col;

    if (row >= OLED_ROW_MAX)
    {
        return;
    }

    for (col = 0; col < OLED_WIDTH; col++)
    {
        s_gram[row][col] = 0x00;
    }
}

void OLED_Refresh(void)
{
    uint8_t page;

    for (page = 0; page < OLED_PAGE_COUNT; page++)
    {
        OledWriteCmd((uint8_t)(0xB0 | page));   /* 定位到第 page 页 */
        OledWriteCmd(0x00);                     /* 列地址低 4 位 */
        OledWriteCmd(0x10);                     /* 列地址高 4 位 */
        OledWriteData(s_gram[page], OLED_WIDTH);
    }
}

/* 把一个字符写进显存。字模是按行存的（每个字节一行，bit7 最左），
   而 SSD1306 显存是按列存的（每个字节一列上的 8 个像素），
   所以这里要做一次行列转置。 */
void OLED_ShowChar(uint8_t col, uint8_t row, char ch)
{
    const uint8_t *glyph;
    uint8_t colIdx;
    uint8_t bitIdx;
    uint8_t pageByte;

    if ((col >= OLED_COL_MAX) || (row >= OLED_ROW_MAX))
    {
        return;
    }

    if (((uint8_t)ch < FONT8X8_FIRST_CHAR) || ((uint8_t)ch > FONT8X8_LAST_CHAR))
    {
        ch = '?';
    }
    glyph = g_font8x8[(uint8_t)ch - FONT8X8_FIRST_CHAR];

    for (colIdx = 0; colIdx < OLED_CHAR_W; colIdx++)
    {
        pageByte = 0x00;
        for (bitIdx = 0; bitIdx < 8; bitIdx++)
        {
            if ((glyph[bitIdx] & (uint8_t)(0x80 >> colIdx)) != 0)
            {
                pageByte |= (uint8_t)(1 << bitIdx);
            }
        }
        s_gram[row][(col * OLED_CHAR_W) + colIdx] = pageByte;
    }
}

void OLED_ShowString(uint8_t col, uint8_t row, const char *str)
{
    while ((*str != '\0') && (col < OLED_COL_MAX))
    {
        OLED_ShowChar(col, row, *str);
        col++;
        str++;
    }
}

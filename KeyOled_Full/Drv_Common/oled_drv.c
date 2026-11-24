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
#include "cn_font16.h"

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

/* 当前使用的从机地址：OLED_Probe 自动探测后确定（0x78 或 0x7A）*/
static uint8_t s_i2cAddr = OLED_I2C_ADDR_A;

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
    (void)I2cWriteByte(s_i2cAddr);
    (void)I2cWriteByte(0x00);
    (void)I2cWriteByte(cmd);
    I2cStop();
}

static void OledWriteData(const uint8_t *buf, uint16_t len)
{
    uint16_t i;

    I2cStart();
    (void)I2cWriteByte(s_i2cAddr);
    (void)I2cWriteByte(0x40);
    for (i = 0; i < len; i++)
    {
        (void)I2cWriteByte(buf[i]);
    }
    I2cStop();
}

/* 试一个从机地址，返回 1 = 有应答。
 * 只发地址字节、马上 STOP，不动显存，对屏没有任何副作用。*/
static uint8_t I2cProbeAddr(uint8_t addr)
{
    uint8_t ack;

    I2cStart();
    ack = I2cWriteByte(addr);       /* 返回 0 表示从机应答了 */
    I2cStop();

    return (uint8_t)((ack == 0u) ? 1u : 0u);
}

/* 自动识别屏的从机地址：
 *   0.86/0.96 寸模块的 SA0 有的焊低、有的焊高，对应地址就是 0x78 / 0x7A。
 *   上电先各试一次，哪个有应答就用哪个；都没应答就退回默认地址，
 *   后面照常按默认地址发数据（屏不亮时串口会报 NO ACK，方便查线）。*/
uint8_t OLED_Probe(void)
{
    if (I2cProbeAddr(OLED_I2C_ADDR_A) != 0u)
    {
        s_i2cAddr = OLED_I2C_ADDR_A;
        return 1u;
    }

    if (I2cProbeAddr(OLED_I2C_ADDR_B) != 0u)
    {
        s_i2cAddr = OLED_I2C_ADDR_B;
        return 2u;
    }

    s_i2cAddr = OLED_I2C_ADDR_A;
    return 0u;
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

    /* 先认一下屏：0x78 没有应答就试 0x7A，选中之后所有读写都用这个地址 */
    (void)OLED_Probe();

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

/* ========================= 反白显示与进度条 ========================= */

/* 整行填满：row 行 128 个字节全写 0xFF，配合取反字符做反白标题栏 */
void OLED_FillRow(uint8_t row)
{
    uint8_t col;

    if (row >= OLED_ROW_MAX)
    {
        return;
    }

    for (col = 0; col < OLED_WIDTH; col++)
    {
        s_gram[row][col] = 0xFF;
    }
}

/* 反白字符：与 OLED_ShowChar 同样的行列转置，只是写入时整字节取反——
 * 背景已经由 OLED_FillRow 填成全亮，取反后字模为 1 的像素变暗，
 * 视觉上就是「亮底暗字」。 */
void OLED_ShowCharInv(uint8_t col, uint8_t row, char ch)
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
        s_gram[row][(col * OLED_CHAR_W) + colIdx] = (uint8_t)~pageByte;
    }
}

void OLED_ShowStringInv(uint8_t col, uint8_t row, const char *str)
{
    while ((*str != '\0') && (col < OLED_COL_MAX))
    {
        OLED_ShowCharInv(col, row, *str);
        col++;
        str++;
    }
}

/* 整行进度条：每格 8 像素宽，前 6 列实心、后 2 列留空，格子之间有可见间隔。
 * lit = 点亮的格子数（0~cells），用在呼吸占空比条这类电平指示上。 */
void OLED_BarRow(uint8_t row, uint8_t cells, uint8_t lit)
{
    uint8_t g;
    uint8_t i;

    if (row >= OLED_ROW_MAX)
    {
        return;
    }
    if (cells > OLED_COL_MAX)
    {
        cells = OLED_COL_MAX;
    }
    if (lit > cells)
    {
        lit = cells;
    }

    OLED_ClearLine(row);
    for (g = 0; g < lit; g++)
    {
        for (i = 0; i < 6; i++)
        {
            s_gram[row][(g * OLED_CHAR_W) + i] = 0xFF;
        }
    }
}

/* 放大字：把 8x8 字模的行、列各复制一遍，得到 16x16 的字形。
 * 行方向放大后一个字要占两页：原字模第 0~3 行进 page，第 4~7 行进 page+1。
 * 每一行像素在原显存里是 1 个 bit，放大后变成相邻的 2 个 bit（0x03 掩码）。*/
void OLED_ShowCharBig(uint8_t col, uint8_t page, char ch)
{
    const uint8_t *glyph;
    uint8_t colIdx;
    uint8_t bitIdx;
    uint8_t lo;
    uint8_t hi;

    if ((col >= OLED_BIG_COL_MAX) || (page >= (OLED_PAGE_COUNT - 1u)))
    {
        return;
    }

    if (((uint8_t)ch < FONT8X8_FIRST_CHAR) || ((uint8_t)ch > FONT8X8_LAST_CHAR))
    {
        ch = '?';
    }

    /* 小数点走特殊路径：字模里的点太小（放大后 4x4），屏上几乎看不出来，
       直接画一个 6x6 实心方块，贴着底线、在 16 像素宽的格子里水平居中 */
    if (ch == '.')
    {
        uint8_t x = (uint8_t)(col * OLED_BIG_CHAR_W +
                              ((OLED_BIG_CHAR_W - OLED_BIG_DOT_W) / 2u));
        for (colIdx = 0; colIdx < OLED_BIG_DOT_W; colIdx++)
        {
            s_gram[page + 1u][x + colIdx] |= OLED_BIG_DOT_MASK;
        }
        return;
    }

    glyph = g_font8x8[(uint8_t)ch - FONT8X8_FIRST_CHAR];

    for (colIdx = 0; colIdx < OLED_CHAR_W; colIdx++)
    {
        lo = 0x00;
        hi = 0x00;

        for (bitIdx = 0; bitIdx < 8; bitIdx++)
        {
            if ((glyph[bitIdx] & (uint8_t)(0x80 >> colIdx)) != 0)
            {
                if (bitIdx < 4)
                {
                    lo |= (uint8_t)(0x03u << (bitIdx * 2));
                }
                else
                {
                    hi |= (uint8_t)(0x03u << ((bitIdx - 4) * 2));
                }
            }
        }

        /* 列方向也放大 2 倍：同一列数据写进相邻两个显存列 */
        s_gram[page][(col * OLED_BIG_CHAR_W) + (colIdx * 2)]            = lo;
        s_gram[page][(col * OLED_BIG_CHAR_W) + (colIdx * 2) + 1u]       = lo;
        s_gram[page + 1u][(col * OLED_BIG_CHAR_W) + (colIdx * 2)]       = hi;
        s_gram[page + 1u][(col * OLED_BIG_CHAR_W) + (colIdx * 2) + 1u]  = hi;
    }
}

void OLED_ShowStringBig(uint8_t col, uint8_t page, const char *str)
{
    while ((*str != '\0') && (col < OLED_BIG_COL_MAX))
    {
        OLED_ShowCharBig(col, page, *str);
        col++;
        str++;
    }
}

/* ========================= 中文（16x16 字库）========================= */

/* 画一个 16x16 汉字。字模是“行优先、每行 2 字节、高位在左”，
 * SSD1306 显存是“列优先、每字节 8 行、bit0 在上”，所以要做行列转置：
 * 上半个字（前 8 行）进 page，下半个字（后 8 行）进 page+1。 */
void OLED_ShowCNChar(uint8_t col, uint8_t page, uint16_t gbk)
{
    const CnGlyph16_t *glyph;
    uint8_t            base;
    uint8_t            x;
    uint8_t            y;
    uint8_t            lo;
    uint8_t            hi;

    if ((col >= OLED_BIG_COL_MAX) || (page >= (OLED_PAGE_COUNT - 1u)))
    {
        return;
    }

    glyph = CnFont16_Lookup(gbk);
    base  = (uint8_t)(col * CN_FONT16_W);

    for (x = 0; x < CN_FONT16_W; x++)
    {
        if (glyph == 0)
        {
            lo = 0x7E;                          /* 字库缺字：画个示意方块 */
            hi = 0x7E;
        }
        else
        {
            lo = 0x00;
            hi = 0x00;

            for (y = 0; y < 8; y++)
            {
                if (((glyph->data[y * 2u + (x >> 3)] >> (7u - (x & 7u))) & 1u) != 0u)
                {
                    lo |= (uint8_t)(1u << y);
                }
            }
            for (y = 0; y < 8; y++)
            {
                if (((glyph->data[(y + 8u) * 2u + (x >> 3)] >> (7u - (x & 7u))) & 1u) != 0u)
                {
                    hi |= (uint8_t)(1u << y);
                }
            }
        }

        s_gram[page][base + x]          = lo;
        s_gram[page + 1u][base + x]     = hi;
    }
}

/* 显示一串汉字。输入必须是 GBK 双字节字节串（见 cn_msg.h 的宏），
 * 长度按“两个字节一个字”解析，不足或越界自动停。 */
void OLED_ShowCNString(uint8_t col, uint8_t page, const char *gbkStr)
{
    while ((gbkStr[0] != '\0') && (gbkStr[1] != '\0') && (col < OLED_BIG_COL_MAX))
    {
        uint16_t code;

        code = (uint16_t)(((uint16_t)(uint8_t)gbkStr[0] << 8) | (uint8_t)gbkStr[1]);
        OLED_ShowCNChar(col, page, code);
        col++;
        gbkStr += 2;
    }
}

/* ---------------------------------------------------------------------------
 * 像素级横坐标版汉字显示
 *
 * 为什么需要它：OLED_ShowCNChar 的 col 单位是 16 像素，只能落在 0/16/32/... 上。
 * 3 个汉字共 48 像素，居中需要左边留 (128-48)/2 = 40 像素 —— 40 不是 16 的倍数，
 * 用 col 表达不了（col=2 左空 32、col=3 左空 48，都偏）。所以这里再提供一套
 * 直接按像素列定位的版本，专供"居中显示几个字"这种小工程用。
 * ------------------------------------------------------------------------- */

/* x 是像素列，合法范围 0 ~ OLED_WIDTH-16；page 与 OLED_ShowCNChar 同义 */
void OLED_ShowCNCharAt(uint8_t x, uint8_t page, uint16_t gbk)
{
    const CnGlyph16_t *glyph;
    uint8_t            i;
    uint8_t            y;
    uint8_t            lo;
    uint8_t            hi;

    if ((((uint16_t)x + CN_FONT16_W) > OLED_WIDTH) || (page >= (OLED_PAGE_COUNT - 1u)))
    {
        return;
    }

    glyph = CnFont16_Lookup(gbk);

    for (i = 0; i < CN_FONT16_W; i++)
    {
        if (glyph == 0)
        {
            lo = 0x7E;                          /* 字库缺字：画个示意方块 */
            hi = 0x7E;
        }
        else
        {
            lo = 0x00;
            hi = 0x00;

            for (y = 0; y < 8; y++)
            {
                if (((glyph->data[y * 2u + (i >> 3)] >> (7u - (i & 7u))) & 1u) != 0u)
                {
                    lo |= (uint8_t)(1u << y);
                }
            }
            for (y = 0; y < 8; y++)
            {
                if (((glyph->data[(y + 8u) * 2u + (i >> 3)] >> (7u - (i & 7u))) & 1u) != 0u)
                {
                    hi |= (uint8_t)(1u << y);
                }
            }
        }

        s_gram[page][x + i]          = lo;
        s_gram[page + 1u][x + i]     = hi;
    }
}

/* 从像素列 x 起连续显示一串汉字，放不下自动截断 */
void OLED_ShowCNStringAt(uint8_t x, uint8_t page, const char *gbkStr)
{
    while ((gbkStr[0] != '\0') && (gbkStr[1] != '\0')
           && (((uint16_t)x + CN_FONT16_W) <= OLED_WIDTH))
    {
        uint16_t code;

        code = (uint16_t)(((uint16_t)(uint8_t)gbkStr[0] << 8) | (uint8_t)gbkStr[1]);
        OLED_ShowCNCharAt(x, page, code);
        x = (uint8_t)(x + CN_FONT16_W);
        gbkStr += 2;
    }
}

/* 按像素宽度水平居中显示一串汉字。
 * 纵向建议传 page = 1：字模占 y = 8~23，正好在 32 行屏上垂直居中
 * （page=0 贴顶、page=2 贴底，都不居中）。 */
void OLED_ShowCNStringCenter(uint8_t page, const char *gbkStr)
{
    uint16_t n = 0u;
    uint16_t w;

    while ((gbkStr[n * 2u] != '\0') && (gbkStr[n * 2u + 1u] != '\0'))
    {
        n++;
    }

    w = (uint16_t)(n * CN_FONT16_W);
    if (w > OLED_WIDTH)
    {
        OLED_ShowCNStringAt(0u, page, gbkStr);      /* 一行放不下，从左边开始截断 */
        return;
    }

    OLED_ShowCNStringAt((uint8_t)((OLED_WIDTH - w) / 2u), page, gbkStr);
}

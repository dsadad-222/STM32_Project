/**
  ******************************************************************************
  * @file    Drv_Common/w25q64_drv.c
  * @brief   片外 SPI Flash W25Q64（8MB）驱动实现
  *
  *          时序要点：
  *            1. CS# 拉低到拉高之间才是一条完整命令，命令 + 地址 + 数据
  *               全部在这段里完成，中间不能松开；
  *            2. 每次"写/擦"之前必须先发 0x06 Write Enable，否则芯片会
  *               默默忽略（这是最常见的"写不进去"原因）；
  *            3. 写/擦期间状态寄存器 bit0(BUSY)=1，必须轮询等它变 0 才能
  *               发下一条命令，这里带超时保护，芯片异常也不会卡死主循环。
  ******************************************************************************
  */

#include "w25q64_drv.h"

/* ---------------- W25Q64 命令字 ---------------- */
#define CMD_WRITE_ENABLE    0x06u   /* 写使能 */
#define CMD_READ_STATUS1    0x05u   /* 读状态寄存器 1 */
#define CMD_READ_DATA       0x03u   /* 读数据（24 位地址）*/
#define CMD_PAGE_PROGRAM    0x02u   /* 页编程（最多 256 字节）*/
#define CMD_SECTOR_ERASE    0x20u   /* 4KB 扇区擦除 */
#define CMD_JEDEC_ID        0x9Fu   /* 读 JEDEC ID（3 字节）*/
#define CMD_RELEASE_PD      0xABu   /* 退出掉电模式（顺带读器件 ID）*/

/* 状态寄存器 1 的位 */
#define STATUS_BUSY         0x01u   /* 1 = 内部正在擦/写 */
#define STATUS_WEL          0x02u   /* 1 = 写使能已置位 */

static uint8_t s_present = 0u;      /* 开机检测结果：1 = 芯片在 */

/* ============================ 底层收发 ============================ */

static void Cs_Low(void)
{
    GPIO_ResetBits(W25Q64_CS_PORT, W25Q64_CS_PIN);
}

static void Cs_High(void)
{
    GPIO_SetBits(W25Q64_CS_PORT, W25Q64_CS_PIN);
}

/* 收发一个字节。带忙等上限：SPI 外设异常时返回 0，绝不在这里死等。 */
static uint8_t Spi_Transfer(uint8_t tx)
{
    uint32_t guard;

    guard = W25Q64_SPI_TIMEOUT;
    while (SPI_I2S_GetFlagStatus(W25Q64_SPI, SPI_I2S_FLAG_TXE) == RESET)
    {
        if (--guard == 0u)
        {
            return 0u;
        }
    }
    SPI_I2S_SendData(W25Q64_SPI, tx);

    guard = W25Q64_SPI_TIMEOUT;
    while (SPI_I2S_GetFlagStatus(W25Q64_SPI, SPI_I2S_FLAG_RXNE) == RESET)
    {
        if (--guard == 0u)
        {
            return 0u;
        }
    }

    return (uint8_t)SPI_I2S_ReceiveData(W25Q64_SPI);
}

/* 发 24 位地址（高字节在前）*/
static void SendAddr(uint32_t addr)
{
    Spi_Transfer((uint8_t)((addr >> 16) & 0xFFu));
    Spi_Transfer((uint8_t)((addr >> 8) & 0xFFu));
    Spi_Transfer((uint8_t)(addr & 0xFFu));
}

/* ============================ 状态操作 ============================ */

static uint8_t ReadStatus(void)
{
    uint8_t st;

    Cs_Low();
    Spi_Transfer(CMD_READ_STATUS1);
    st = Spi_Transfer(0xFFu);
    Cs_High();

    return st;
}

/* 等 BUSY 清掉。返回 1 = 就绪，0 = 超时 */
static uint8_t WaitReady(void)
{
    uint32_t guard = W25Q64_BUSY_TIMEOUT;

    while ((ReadStatus() & STATUS_BUSY) != 0u)
    {
        if (--guard == 0u)
        {
            return 0u;
        }
    }

    return 1u;
}

/* 置写使能位。返回 1 = WEL 已置上 */
static uint8_t WriteEnable(void)
{
    Cs_Low();
    Spi_Transfer(CMD_WRITE_ENABLE);
    Cs_High();

    return (uint8_t)(((ReadStatus() & STATUS_WEL) != 0u) ? 1u : 0u);
}

/* ============================ 对外接口 ============================ */

uint32_t W25Q64_ReadID(void)
{
    uint32_t id;
    uint8_t  b0;
    uint8_t  b1;
    uint8_t  b2;

    Cs_Low();
    Spi_Transfer(CMD_JEDEC_ID);
    b0 = Spi_Transfer(0xFFu);
    b1 = Spi_Transfer(0xFFu);
    b2 = Spi_Transfer(0xFFu);
    Cs_High();

    id = ((uint32_t)b0 << 16) | ((uint32_t)b1 << 8) | (uint32_t)b2;

    return id;
}

uint8_t W25Q64_Init(void)
{
    GPIO_InitTypeDef gpio;
    SPI_InitTypeDef  spi;
    uint32_t         id1;
    uint32_t         id2;

    RCC_APB2PeriphClockCmd(W25Q64_CS_CLK, ENABLE);
    RCC_APB1PeriphClockCmd(W25Q64_SPI_CLK, ENABLE);

    /* CS 先输出高（未选中）再初始化 SPI 外设，避免上电瞬间被当成命令起始 */
    GPIO_SetBits(W25Q64_CS_PORT, W25Q64_CS_PIN);
    gpio.GPIO_Pin   = W25Q64_CS_PIN;
    gpio.GPIO_Mode  = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(W25Q64_CS_PORT, &gpio);
    Cs_High();

    /* SCK(PB13) / MOSI(PB15) 复用推挽输出 */
    gpio.GPIO_Pin  = GPIO_Pin_13 | GPIO_Pin_15;
    gpio.GPIO_Mode = GPIO_Mode_AF_PP;
    GPIO_Init(GPIOB, &gpio);

    /* MISO(PB14) 浮空输入（板上 Flash 的 DO 脚是推挽输出，不需要内部上拉）*/
    gpio.GPIO_Pin  = GPIO_Pin_14;
    gpio.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOB, &gpio);

    SPI_I2S_DeInit(W25Q64_SPI);
    spi.SPI_Direction         = SPI_Direction_2Lines_FullDuplex;
    spi.SPI_Mode              = SPI_Mode_Master;
    spi.SPI_DataSize          = SPI_DataSize_8b;
    spi.SPI_CPOL              = SPI_CPOL_High;          /* 空闲高 */
    spi.SPI_CPHA              = SPI_CPHA_2Edge;         /* 第二个边沿采样 = SPI Mode 3 */
    spi.SPI_NSS               = SPI_NSS_Soft;
    spi.SPI_BaudRatePrescaler = SPI_BaudRatePrescaler_4;/* 36MHz / 4 = 9MHz */
    spi.SPI_FirstBit          = SPI_FirstBit_MSB;
    spi.SPI_CRCPolynomial     = 7u;
    SPI_Init(W25Q64_SPI, &spi);
    SPI_Cmd(W25Q64_SPI, ENABLE);

    /* 读两次 ID 取一致值：悬空引脚偶尔会读到随机数，连读两次能滤掉 */
    id1 = W25Q64_ReadID();
    id2 = W25Q64_ReadID();

    s_present = ((id1 == W25Q64_JEDEC_ID) && (id2 == W25Q64_JEDEC_ID)) ? 1u : 0u;

    return s_present;
}

uint8_t W25Q64_IsPresent(void)
{
    return s_present;
}

void W25Q64_Read(uint32_t addr, uint8_t *buf, uint16_t len)
{
    uint16_t i;

    if (s_present == 0u)
    {
        return;
    }
    if ((buf == 0) || (len == 0u))
    {
        return;
    }
    if ((addr + (uint32_t)len) > W25Q64_CAPACITY)
    {
        return;
    }

    Cs_Low();
    Spi_Transfer(CMD_READ_DATA);
    SendAddr(addr);
    for (i = 0u; i < len; i++)
    {
        buf[i] = Spi_Transfer(0xFFu);
    }
    Cs_High();
}

uint8_t W25Q64_EraseSector(uint32_t addr)
{
    if (s_present == 0u)
    {
        return 0u;
    }
    if (addr >= W25Q64_CAPACITY)
    {
        return 0u;
    }
    if (WriteEnable() == 0u)
    {
        return 0u;
    }

    Cs_Low();
    Spi_Transfer(CMD_SECTOR_ERASE);
    SendAddr(addr);
    Cs_High();

    return WaitReady();
}

uint8_t W25Q64_PageProgram(uint32_t addr, const uint8_t *buf, uint16_t len)
{
    uint16_t i;

    if (s_present == 0u)
    {
        return 0u;
    }
    if ((buf == 0) || (len == 0u))
    {
        return 0u;
    }
    if ((addr + (uint32_t)len) > W25Q64_CAPACITY)
    {
        return 0u;
    }
    /* 一次页编程不能跨页：越界就拒掉，由 W25Q64_WriteData 负责切页 */
    if (((addr % W25Q64_PAGE_SIZE) + (uint32_t)len) > W25Q64_PAGE_SIZE)
    {
        return 0u;
    }
    if (WriteEnable() == 0u)
    {
        return 0u;
    }

    Cs_Low();
    Spi_Transfer(CMD_PAGE_PROGRAM);
    SendAddr(addr);
    for (i = 0u; i < len; i++)
    {
        Spi_Transfer(buf[i]);
    }
    Cs_High();

    return WaitReady();
}

uint8_t W25Q64_WriteData(uint32_t addr, const uint8_t *buf, uint16_t len)
{
    uint32_t sector;
    uint32_t last;
    uint32_t a;
    uint16_t written;
    uint16_t chunk;
    uint16_t pageLeft;

    if (s_present == 0u)
    {
        return 0u;
    }
    if ((buf == 0) || (len == 0u))
    {
        return 0u;
    }
    if ((addr + (uint32_t)len) > W25Q64_CAPACITY)
    {
        return 0u;
    }

    /* 1) 擦掉本次写入覆盖到的所有扇区 */
    last = addr + (uint32_t)len - 1u;
    for (sector = (addr / W25Q64_SECTOR_SIZE) * W25Q64_SECTOR_SIZE;
         sector <= last;
         sector += W25Q64_SECTOR_SIZE)
    {
        if (W25Q64_EraseSector(sector) == 0u)
        {
            return 0u;
        }
    }

    /* 2) 逐页写，遇到页边界自动切页 */
    a       = addr;
    written = 0u;
    while (written < len)
    {
        pageLeft = (uint16_t)(W25Q64_PAGE_SIZE - (a % W25Q64_PAGE_SIZE));
        chunk    = (uint16_t)(len - written);
        if (chunk > pageLeft)
        {
            chunk = pageLeft;
        }
        if (W25Q64_PageProgram(a, &buf[written], chunk) == 0u)
        {
            return 0u;
        }
        a       += chunk;
        written  = (uint16_t)(written + chunk);
    }

    return 1u;
}

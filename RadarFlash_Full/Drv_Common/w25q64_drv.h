/**
  ******************************************************************************
  * @file    Drv_Common/w25q64_drv.h
  * @brief   片外 SPI Flash W25Q64（8MB，U9）读写驱动
  *
  *          板上接线（原理图 U9 W25Q64JVSSIQ，网络标签 SPI2_xxx）：
  *              CLK  (pin6) -> PB13  SPI2_SCK
  *              DO   (pin2) -> PB14  SPI2_MISO
  *              DI   (pin5) -> PB15  SPI2_MOSI
  *              CS#  (pin1) -> PB12  （软件片选，普通推挽输出）
  *              WP# / HOLD# 板上已固定为高，不占用 IO
  *          旁边 J4 排针同样引出 PB12/PB13/PB14，与 Flash 共用这条 SPI2 总线。
  *
  *          注意：W25Q64 一次只能写"一页"（256 字节），写之前必须先擦掉
  *          整个扇区（4KB）—— Flash 的存储单元只能把 1 变成 0，擦除是把
  *          整块拉回全 1，所以"改一个字节"= 擦一扇区 + 重写整条记录。
  ******************************************************************************
  */

#ifndef __W25Q64_DRV_H
#define __W25Q64_DRV_H

#include "stm32f10x.h"

/* ---------------- 硬件映射 ---------------- */
#define W25Q64_CS_PORT          GPIOB
#define W25Q64_CS_PIN           GPIO_Pin_12
#define W25Q64_CS_CLK           RCC_APB2Periph_GPIOB
#define W25Q64_SPI_CLK          RCC_APB1Periph_SPI2
#define W25Q64_SPI              SPI2

/* ---------------- 容量参数 ---------------- */
#define W25Q64_PAGE_SIZE        256u                    /* 页大小（一次最多写这么多）*/
#define W25Q64_SECTOR_SIZE      4096u                   /* 扇区大小（最小擦除单位）*/
#define W25Q64_BLOCK_SIZE       65536u                  /* 块大小（64KB 擦除）*/
#define W25Q64_CAPACITY         (8u * 1024u * 1024u)    /* 总容量 8MB */

/* W25Q64 的 JEDEC ID：厂商 0xEF(Winbond) + 类型 0x40 + 容量 0x17(8MB) */
#define W25Q64_JEDEC_ID         0xEF4017u
#define W25Q64_ID_ABSENT        0x000000u               /* MISO 被拉低时读到全 0 */
#define W25Q64_ID_OPEN          0xFFFFFFu               /* 没接/没焊时读到全 1 */

/* 单次传输的忙等上限（约几十微秒 @9MHz），防止芯片异常时卡死在死循环 */
#define W25Q64_SPI_TIMEOUT      0x2000u
/* 擦除/写入后的 BUSY 轮询上限（扇区擦除典型 45ms，给足余量）*/
#define W25Q64_BUSY_TIMEOUT     0x00FFFFFFu

/* ============================ 接口 ============================ */

/* 初始化 SPI2 + CS，并读一次 ID 判断芯片在不在。
 * 返回 1 = 检测到 W25Q64（ID 匹配），0 = 没检测到（未焊接/接线异常）*/
uint8_t  W25Q64_Init(void);

/* 读 JEDEC ID（3 字节合成 0xEF4017）。芯片不在时返回 0x000000 或 0xFFFFFF */
uint32_t W25Q64_ReadID(void);

/* 最近一次初始化时是否检测到芯片（1=在，0=不在），不重新访问总线 */
uint8_t  W25Q64_IsPresent(void);

/* 读数据：addr 为 24 位字节地址，len 最大不超过容量 */
void     W25Q64_Read(uint32_t addr, uint8_t *buf, uint16_t len);

/* 擦除 addr 所在的 4KB 扇区。返回 1 = 成功，0 = 超时/失败 */
uint8_t  W25Q64_EraseSector(uint32_t addr);

/* 页内写入：addr 必须落在同一页内且 addr%256 + len <= 256。
 * 返回 1 = 成功，0 = 参数越界或超时 */
uint8_t  W25Q64_PageProgram(uint32_t addr, const uint8_t *buf, uint16_t len);

/* 写数据（供上层直接用）：先擦掉覆盖到的所有扇区，再逐页写。
 * 注意会清掉这些扇区里的其他内容。返回 1 = 成功 */
uint8_t  W25Q64_WriteData(uint32_t addr, const uint8_t *buf, uint16_t len);

#endif /* __W25Q64_DRV_H */

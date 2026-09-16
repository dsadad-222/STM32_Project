/**
  ******************************************************************************
  * @file    Drv_Common/flash_drv.h
  * @brief   内部 Flash 掉电保存（保存串口下发的文本与设备状态）
  *
  *          STM32F103ZE 属于大容量产品：主存储区 512KB、页大小 2KB、共 256 页。
  *          程序只占最前面几 KB，所以拿最后一页当数据页，地址是
  *          0x08000000 + 256 * 2KB - 2KB = 0x0807F800。
  *
  *          记录里放了魔数和累加和校验：从没写过、或者上次写到一半掉电，
  *          读出来都算无效，开机时不会把垃圾数据当参数用。
  *
  *          注意 text 是"定长字段"而不是 C 字符串：它固定占 STORE_TEXT_MAX
  *          个字节，不足的部分用空格补齐，有效字符个数由 textLen 给出。
  *          这样就不必关心结尾有没有 '\0'，存储和显示都不会越界。
  ******************************************************************************
  */

#ifndef __FLASH_DRV_H
#define __FLASH_DRV_H

#include "stm32f10x.h"

#define STORE_PAGE_ADDR     0x0807F800u     /* 数据页起始地址（最后一页）*/
#define STORE_MAGIC         0x5A5AA5A5u     /* 记录有效标志 */
#define STORE_TEXT_MAX      32              /* 最多保存 32 个字符 */

/* 设备状态位（放在 flags 里）*/
#define STORE_BIT_LEFT      (1u << 0)
#define STORE_BIT_RIGHT     (1u << 1)
#define STORE_BIT_BEEP      (1u << 2)
#define STORE_BIT_LED       (1u << 3)

/* 字段按 4 字节对齐排列，结构体不会有隐式填充：4+4+4+32+2+2 = 48 字节，
   校验范围就是 sizeof(StoreRecord_t) - 4（末尾 4 字节是 checksum + reserved）。*/
typedef struct
{
    uint32_t magic;                     /* 魔数，等于 STORE_MAGIC 才算有效 */
    uint32_t flags;                     /* 设备状态位 */
    uint32_t textLen;                   /* text 里有效字符个数（0~32）*/
    char     text[STORE_TEXT_MAX];      /* 串口下发的文本，空格填充 */
    uint16_t checksum;                  /* 前面所有字节的累加和 */
    uint16_t reserved;                  /* 占位，凑齐 4 字节对齐 */
} StoreRecord_t;

uint8_t Store_Load(StoreRecord_t *rec);                 /* 1 = 读到了有效记录 */
uint8_t Store_Save(StoreRecord_t *rec);                 /* 1 = 写入成功 */
void    Store_Clear(void);                              /* 擦除数据页 */
uint8_t Store_IsSame(const StoreRecord_t *a, const StoreRecord_t *b);

#endif /* __FLASH_DRV_H */

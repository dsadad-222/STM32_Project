/**
  ******************************************************************************
  * @file    Drv_Common/nvstore.h
  * @brief   Power fail safe parameter block kept in the internal flash.
  *
  *          STM32F103ZE is a high density part: 512 KB of main memory split
  *          into 2 KB pages, 256 of them.  The image only occupies the first
  *          few KB, so the very last page is reserved as a data page and lives
  *          at 0x08000000 + 256 * 2 KB - 2 KB = 0x0807F800.
  *
  *          A tag word plus a byte sum guard the block.  A page that was never
  *          written, or a write that was cut short by a power loss, fails both
  *          checks and is reported as "no data" instead of being used.
  *
  *          text is a plain fixed size byte field, not a C string: nchars says
  *          how many of the NV_TEXT_LEN characters are meaningful and the rest
  *          are padded with spaces.  That way neither the store nor the panel
  *          code ever has to worry about a terminator.
  ******************************************************************************
  */

#ifndef NVSTORE_H
#define NVSTORE_H

#include <stdint.h>

#define NV_PAGE_ADDR        0x0807F800UL
#define NV_TAG              0x5A5AA5A5UL
#define NV_TEXT_LEN         32U

/* Bit positions inside nv_block_t::state */
#define NV_BIT_LEFT         (1UL << 0)
#define NV_BIT_RIGHT        (1UL << 1)
#define NV_BIT_BEEP         (1UL << 2)
#define NV_BIT_STRIP        (1UL << 3)

typedef struct
{
    uint32_t tag;                       /* NV_TAG when the block is valid */
    uint32_t state;                     /* actuator bits                  */
    uint32_t nchars;                    /* 0 .. NV_TEXT_LEN               */
    char     text[NV_TEXT_LEN];         /* space padded payload           */
    uint16_t sum;                       /* byte sum over everything before */
    uint16_t spare;                     /* keeps the block 4 byte aligned  */
} nv_block_t;

uint8_t nv_read(nv_block_t *blk);               /* 1 = a valid block was read */
uint8_t nv_write(nv_block_t *blk);              /* 1 = committed to flash     */
void    nv_erase(void);
uint8_t nv_equal(const nv_block_t *a, const nv_block_t *b);

#endif /* NVSTORE_H */

/**
  ******************************************************************************
  * @file    Drv_Common/flash_drv.c
  * @brief   内部 Flash 掉电保存的实现
  *
  *          写入固定流程：解锁 -> 擦页 -> 按半字逐次编程 -> 上锁。
  *          STM32 的内部 Flash 只能把 1 改成 0，要重新写就得先整页擦掉，
  *          所以每次保存都是"擦一页再写一条记录"。
  ******************************************************************************
  */

#include "flash_drv.h"

/* 参与校验的字节数：末尾 4 字节是 checksum + reserved，不算进去 */
#define STORE_CHECK_LEN     (sizeof(StoreRecord_t) - 4u)

/* 累加和校验：把参与校验的字节全部加起来 */
static uint16_t Store_CalcChecksum(const StoreRecord_t *rec)
{
    const uint8_t *p = (const uint8_t *)rec;
    uint16_t sum = 0;
    uint16_t i;

    for (i = 0; i < (uint16_t)STORE_CHECK_LEN; i++)
    {
        sum = (uint16_t)(sum + p[i]);
    }

    return sum;
}

/* 长度越界就把长度收回来，避免 textLen 指向数组外面 */
static void Store_ClampLen(StoreRecord_t *rec)
{
    if (rec->textLen > STORE_TEXT_MAX)
    {
        rec->textLen = STORE_TEXT_MAX;
    }
}

uint8_t Store_Load(StoreRecord_t *rec)
{
    const StoreRecord_t *flashRec = (const StoreRecord_t *)STORE_PAGE_ADDR;

    if (flashRec->magic != STORE_MAGIC)
    {
        return 0;                       /* 从没写过，或已经被擦除 */
    }
    if (flashRec->textLen > STORE_TEXT_MAX)
    {
        return 0;                       /* 长度越界，数据不可信 */
    }
    if (flashRec->checksum != Store_CalcChecksum(flashRec))
    {
        return 0;                       /* 校验不过，多半是上次写到一半掉电 */
    }

    Store_ClampLen((StoreRecord_t *)flashRec);

    *rec = *flashRec;

    return 1;
}

uint8_t Store_Save(StoreRecord_t *rec)
{
    StoreRecord_t local;
    const uint8_t *src;
    uint32_t addr;
    uint16_t i;
    uint16_t halfWord;

    Store_ClampLen(rec);

    local          = *rec;              /* 在 RAM 里补好魔数和校验再写进去 */
    local.magic    = STORE_MAGIC;
    local.reserved = 0u;
    local.checksum = Store_CalcChecksum(&local);

    FLASH_Unlock();

    if (FLASH_ErasePage(STORE_PAGE_ADDR) != FLASH_COMPLETE)
    {
        FLASH_Lock();
        return 0;
    }

    src  = (const uint8_t *)&local;
    addr = STORE_PAGE_ADDR;
    for (i = 0; i < (uint16_t)sizeof(StoreRecord_t); i += 2u)
    {
        halfWord = (uint16_t)((uint16_t)src[i] | ((uint16_t)src[i + 1u] << 8));
        if (FLASH_ProgramHalfWord(addr, halfWord) != FLASH_COMPLETE)
        {
            FLASH_Lock();
            return 0;
        }
        addr += 2u;
    }

    FLASH_Lock();

    *rec = local;                       /* 把补好的内容回写给调用者 */

    return 1;
}

void Store_Clear(void)
{
    FLASH_Unlock();
    (void)FLASH_ErasePage(STORE_PAGE_ADDR);
    FLASH_Lock();
}

uint8_t Store_IsSame(const StoreRecord_t *a, const StoreRecord_t *b)
{
    uint32_t i;

    if (a->flags != b->flags)
    {
        return 0;
    }
    if (a->textLen != b->textLen)
    {
        return 0;
    }

    for (i = 0; i < a->textLen; i++)
    {
        if (a->text[i] != b->text[i])
        {
            return 0;
        }
    }

    return 1;
}

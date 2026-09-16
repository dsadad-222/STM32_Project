/**
  ******************************************************************************
  * @file    Drv_Common/nvstore.c
  * @brief   Internal flash parameter block, driven through the FLASH registers.
  *
  *          The peripheral library is deliberately not used here; the sequence
  *          is short enough to follow in raw registers:
  *            unlock  -> KEYR = 0x45670123 then 0xCDEF89AB
  *            erase   -> CR.PER = 1, AR = page, CR.STRT = 1, wait for !SR.BSY
  *            program -> CR.PG  = 1, store a half word, wait for !SR.BSY
  *            lock    -> CR.LOCK = 1
  *          SR.EOP is cleared by writing a 1 back into it.
  ******************************************************************************
  */

#include "nvstore.h"
#include "stm32f10x.h"

/* The bit masks come from stm32f10x.h (FLASH_CR_xxx / FLASH_SR_xxx); only the
   register accesses themselves are written by hand here.                       */

/* Everything except the trailing sum / spare pair is covered by the sum. */
#define NV_SUM_LEN          (sizeof(nv_block_t) - 4U)

static uint16_t nv_sum(const nv_block_t *blk)
{
    const uint8_t *p = (const uint8_t *)blk;
    uint16_t total = 0U;
    uint16_t i;

    for (i = 0U; i < (uint16_t)NV_SUM_LEN; i++)
    {
        total = (uint16_t)(total + p[i]);
    }

    return total;
}

static void nv_wait_ready(void)
{
    while ((FLASH->SR & FLASH_SR_BSY) != 0UL)
    {
    }
}

static void nv_clear_flags(void)
{
    FLASH->SR = (FLASH_SR_EOP | FLASH_SR_PGERR | FLASH_SR_WRPRTERR);
}

static void nv_unlock(void)
{
    FLASH->KEYR = FLASH_KEY1;
    FLASH->KEYR = FLASH_KEY2;
}

static void nv_lock(void)
{
    FLASH->CR |= FLASH_CR_LOCK;
}

static void nv_page_erase(uint32_t addr)
{
    nv_wait_ready();
    FLASH->CR |= FLASH_CR_PER;
    FLASH->AR  = addr;
    FLASH->CR |= FLASH_CR_STRT;
    nv_wait_ready();
    FLASH->CR &= ~FLASH_CR_PER;
    nv_clear_flags();
}

static void nv_program_half(uint32_t addr, uint16_t data)
{
    nv_wait_ready();
    FLASH->CR |= FLASH_CR_PG;
    *(volatile uint16_t *)addr = data;
    nv_wait_ready();
    FLASH->CR &= ~FLASH_CR_PG;
    nv_clear_flags();
}

uint8_t nv_read(nv_block_t *blk)
{
    const nv_block_t *stored = (const nv_block_t *)NV_PAGE_ADDR;

    if (stored->tag != NV_TAG)
    {
        return 0U;
    }
    if (stored->nchars > NV_TEXT_LEN)
    {
        return 0U;
    }
    if (stored->sum != nv_sum(stored))
    {
        return 0U;
    }

    *blk = *stored;

    return 1U;
}

uint8_t nv_write(nv_block_t *blk)
{
    nv_block_t local;
    const uint8_t *raw;
    uint32_t addr;
    uint16_t i;
    uint16_t half;

    if (blk->nchars > NV_TEXT_LEN)
    {
        blk->nchars = NV_TEXT_LEN;
    }

    local        = *blk;
    local.tag    = NV_TAG;
    local.spare  = 0U;
    local.sum    = nv_sum(&local);

    nv_unlock();
    nv_page_erase(NV_PAGE_ADDR);

    raw  = (const uint8_t *)&local;
    addr = NV_PAGE_ADDR;
    for (i = 0U; i < (uint16_t)sizeof(nv_block_t); i += 2U)
    {
        half = (uint16_t)((uint16_t)raw[i] | ((uint16_t)raw[i + 1U] << 8));
        nv_program_half(addr, half);
        addr += 2U;
    }
    nv_lock();

    *blk = local;

    return 1U;
}

void nv_erase(void)
{
    nv_unlock();
    nv_page_erase(NV_PAGE_ADDR);
    nv_lock();
}

uint8_t nv_equal(const nv_block_t *a, const nv_block_t *b)
{
    uint32_t i;

    if (a->state != b->state)
    {
        return 0U;
    }
    if (a->nchars != b->nchars)
    {
        return 0U;
    }
    for (i = 0U; i < a->nchars; i++)
    {
        if (a->text[i] != b->text[i])
        {
            return 0U;
        }
    }

    return 1U;
}

/**
  ******************************************************************************
  * @file    Drv_Common/panel.c
  * @brief   SSD1306 128x32 driver with a bit banged I2C bus (PB6 / PB7).
  *
  *          Port B is poked through its registers directly instead of going
  *          through the peripheral library, so the whole bus timing is under
  *          our control:
  *            CRL nibble 0x7 -> output, open drain, 50 MHz
  *            BSRR / BRR     -> release / pull a line low
  *            IDR            -> read the level back for the ACK bit
  ******************************************************************************
  */

#include "panel.h"

/* ---------------------------------------------------------------- bus pins */

#define PIN_SCL             (1U << 6)       /* PB6 */
#define PIN_SDA             (1U << 7)       /* PB7 */

#define CRL_SCL_SHIFT       24U             /* CRL[27:24] -> PB6 */
#define CRL_SDA_SHIFT       28U             /* CRL[31:28] -> PB7 */
#define CRL_NIBBLE_OD50     0x7U            /* open drain output, 50 MHz */
#define CRL_NIBBLE_MASK     0xFU

#define SCL_LOW()           (GPIOB->BRR  = PIN_SCL)
#define SCL_RELEASE()       (GPIOB->BSRR = PIN_SCL)
#define SDA_LOW()           (GPIOB->BRR  = PIN_SDA)
#define SDA_RELEASE()       (GPIOB->BSRR = PIN_SDA)
#define SDA_IS_HIGH()       ((GPIOB->IDR & PIN_SDA) != 0U)

/* Roughly 200 kHz at 72 MHz.  The panel tolerates far slower clocks, so a
   generous delay costs nothing and keeps the timing safe on long wires. */
static void bus_delay(void)
{
    volatile uint8_t n = 12U;

    while (n-- != 0U)
    {
    }
}

static void bus_start(void)
{
    SDA_RELEASE();
    SCL_RELEASE();
    bus_delay();
    SDA_LOW();
    bus_delay();
    SCL_LOW();
    bus_delay();
}

static void bus_stop(void)
{
    SDA_LOW();
    bus_delay();
    SCL_RELEASE();
    bus_delay();
    SDA_RELEASE();
    bus_delay();
}

/* Sends one byte and returns 0 when the slave acknowledged it. */
static uint8_t bus_send(uint8_t byte)
{
    uint8_t bit;
    uint8_t nack;

    for (bit = 0U; bit < 8U; bit++)
    {
        if ((byte & 0x80U) != 0U)
        {
            SDA_RELEASE();
        }
        else
        {
            SDA_LOW();
        }
        byte = (uint8_t)(byte << 1);
        bus_delay();
        SCL_RELEASE();
        bus_delay();
        SCL_LOW();
        bus_delay();
    }

    SDA_RELEASE();                          /* hand the line over for the ACK */
    bus_delay();
    SCL_RELEASE();
    bus_delay();
    nack = SDA_IS_HIGH() ? 1U : 0U;
    SCL_LOW();
    bus_delay();

    return nack;
}

/* Control byte 0x00 introduces a command, 0x40 introduces display data. */
static void panel_cmd(uint8_t cmd)
{
    bus_start();
    (void)bus_send(PANEL_I2C_ADDR);
    (void)bus_send(0x00U);
    (void)bus_send(cmd);
    bus_stop();
}

static void panel_data(const uint8_t *buf, uint16_t len)
{
    uint16_t i;

    bus_start();
    (void)bus_send(PANEL_I2C_ADDR);
    (void)bus_send(0x40U);
    for (i = 0U; i < len; i++)
    {
        (void)bus_send(buf[i]);
    }
    bus_stop();
}

/* ------------------------------------------------------------- shadow ram */

static uint8_t g_pages[PANEL_PAGES][PANEL_W];

/* ------------------------------------------------------------------- api */

void panel_init(void)
{
    RCC->APB2ENR |= RCC_APB2ENR_IOPBEN;

    GPIOB->CRL &= ~((CRL_NIBBLE_MASK << CRL_SCL_SHIFT) |
                    (CRL_NIBBLE_MASK << CRL_SDA_SHIFT));
    GPIOB->CRL |=  ((CRL_NIBBLE_OD50 << CRL_SCL_SHIFT) |
                    (CRL_NIBBLE_OD50 << CRL_SDA_SHIFT));

    SCL_RELEASE();
    SDA_RELEASE();

    panel_cmd(0xAEU);           /* display off while we set things up   */
    panel_cmd(0xD5U);           /* clock divide / oscillator frequency  */
    panel_cmd(0x80U);
    panel_cmd(0xA8U);           /* multiplex ratio: 32 rows             */
    panel_cmd(0x1FU);
    panel_cmd(0xD3U);           /* display offset                       */
    panel_cmd(0x00U);
    panel_cmd(0x40U);           /* start line 0                         */
    panel_cmd(0x8DU);           /* charge pump                          */
    panel_cmd(0x14U);           /* enable it, the module only gets 3V3  */
    panel_cmd(0x20U);           /* addressing mode: page               */
    panel_cmd(0x02U);
    panel_cmd(0xA1U);           /* segment remap                        */
    panel_cmd(0xC8U);           /* COM scan direction, remapped         */
    panel_cmd(0xDAU);           /* COM pins: 0x02 is the 128x32 setting */
    panel_cmd(0x02U);
    panel_cmd(0x81U);           /* contrast                             */
    panel_cmd(0x8FU);
    panel_cmd(0xD9U);           /* pre charge period                    */
    panel_cmd(0xF1U);
    panel_cmd(0xDBU);           /* VCOMH deselect level                 */
    panel_cmd(0x40U);
    panel_cmd(0xA4U);           /* follow the shadow ram                */
    panel_cmd(0xA6U);           /* not inverted                         */
    panel_cmd(0xAFU);           /* display on                           */

    panel_blank();
    panel_flush();
}

void panel_blank(void)
{
    uint8_t page;
    uint8_t col;

    for (page = 0U; page < PANEL_PAGES; page++)
    {
        for (col = 0U; col < PANEL_W; col++)
        {
            g_pages[page][col] = 0x00U;
        }
    }
}

void panel_blank_row(uint8_t row)
{
    uint8_t col;

    if (row < PANEL_ROWS)
    {
        for (col = 0U; col < PANEL_W; col++)
        {
            g_pages[row][col] = 0x00U;
        }
    }
}

void panel_flush(void)
{
    uint8_t page;

    for (page = 0U; page < PANEL_PAGES; page++)
    {
        panel_cmd((uint8_t)(0xB0U | page));
        panel_cmd(0x00U);                   /* column low nibble  */
        panel_cmd(0x10U);                   /* column high nibble */
        panel_data(g_pages[page], PANEL_W);
    }
}

/* The font stores one byte per row while the SSD1306 wants one byte per
   column, so every glyph gets rotated 90 degrees on the way in. */
void panel_putc(uint8_t col, uint8_t row, char c)
{
    const uint8_t *glyph;
    uint8_t x;
    uint8_t y;
    uint8_t column;

    if ((col >= PANEL_COLS) || (row >= PANEL_ROWS))
    {
        return;
    }
    if (((uint8_t)c < GLYPH_FIRST) || ((uint8_t)c > GLYPH_LAST))
    {
        c = '?';
    }
    glyph = g_glyph_8x8[(uint8_t)c - GLYPH_FIRST];

    for (x = 0U; x < GLYPH_W; x++)
    {
        column = 0x00U;
        for (y = 0U; y < GLYPH_H; y++)
        {
            if (((glyph[y] >> (7U - x)) & 0x01U) != 0U)
            {
                column |= (uint8_t)(1U << y);
            }
        }
        g_pages[row][(col * GLYPH_W) + x] = column;
    }
}

void panel_puts(uint8_t col, uint8_t row, const char *s)
{
    while ((*s != '\0') && (col < PANEL_COLS))
    {
        panel_putc(col, row, *s);
        col++;
        s++;
    }
}

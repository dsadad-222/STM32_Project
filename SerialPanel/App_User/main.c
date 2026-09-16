/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   Host driven node: actuators, OLED panel and a power fail safe store.
  *
  *          The host talks over USART1 (PA9 / PA10) at 115200-8-N-1.
  *          A frame looks like this:
  *
  *              0x55 | 0xFF | <n> | <func> | <payload ...>
  *
  *          where <n> counts the function byte plus the payload bytes.  Any
  *          extra trailing byte (a checksum, for instance) is simply ignored,
  *          so both "55 FF 03 06 00" and "55 FF 03 06 00 AA" behave the same.
  *
  *          Function ids
  *            0x06  actuator command, payload is one byte
  *                    0x00 left indicator   (PG14)
  *                    0x01 right indicator  (PG15)
  *                    0x02 buzzer           (PG12)
  *                    0x03 LED strip        (PG0/PG1/PG2)
  *                  Every frame toggles the addressed actuator.  Indicators
  *                  blink at 500 ms per half period while they are on.
  *            0x07  panel text, payload is up to 32 printable ASCII bytes.
  *                  The text is drawn on the OLED and written to the store.
  *            0x08  store housekeeping, payload is one byte
  *                    0x00 commit the current state and text
  *                    0x01 wipe the data page
  *                    0x02 read the data page back and apply it
  *
  *          On start up the internal flash block is read first, so actuator
  *          states and the last text survive a power cycle.
  *
  *          Handy frames to type into a serial terminal:
  *              55 FF 03 06 00     toggle the left indicator
  *              55 FF 03 06 01     toggle the right indicator
  *              55 FF 03 06 02     toggle the buzzer
  *              55 FF 03 06 03     toggle the LED strip
  *              55 FF 06 07 HELLO  show HELLO and store it
  *              55 FF 02 08 02     reload from the store
  *              55 FF 02 08 01     wipe the store
  ******************************************************************************
  */

#include "board.h"
#include "tick.h"
#include "uart.h"
#include "panel.h"
#include "nvstore.h"

/* --------------------------------------------------------------- protocol */

#define SOF0                0x55U
#define SOF1                0xFFU

#define FID_ACTUATOR        0x06U
#define FID_TEXT            0x07U
#define FID_NVRAM           0x08U

#define ACT_LEFT            0x00U
#define ACT_RIGHT           0x01U
#define ACT_BEEP            0x02U
#define ACT_STRIP           0x03U

#define NVRAM_SAVE          0x00U
#define NVRAM_CLEAR         0x01U
#define NVRAM_RELOAD        0x02U

#define RX_CAP              40U         /* biggest payload we accept   */
#define RX_GAP_MS           200U        /* idle gap that voids a frame */
#define BLINK_HALF_MS       500U        /* indicator half period       */

/* ----------------------------------------------------------- description */

typedef struct
{
    uint8_t     code;                   /* value on the wire       */
    uint32_t    bit;                    /* matching bit in g_state */
    const char *label;                  /* shown by report()       */
} actuator_t;

static const actuator_t g_actuators[] =
{
    { ACT_LEFT,  NV_BIT_LEFT,  "LEFT"  },
    { ACT_RIGHT, NV_BIT_RIGHT, "RIGHT" },
    { ACT_BEEP,  NV_BIT_BEEP,  "BEEP"  },
    { ACT_STRIP, NV_BIT_STRIP, "STRIP" }
};

#define ACTUATOR_COUNT      (sizeof(g_actuators) / sizeof(g_actuators[0]))

/* ------------------------------------------------------------------ state */

static uint32_t     g_state       = 0U;                 /* NV_BIT_* flags       */
static char         g_text[NV_TEXT_LEN];                /* space padded payload */
static uint32_t     g_nchars      = 0U;
static char         g_note[PANEL_COLS + 1U];            /* bottom panel line    */
static uint8_t      g_from_nv     = 0U;                 /* booted off the store */
static uint8_t      g_blink_phase = 0U;
static uint32_t     g_blink_at    = 0U;
static nv_block_t   g_shadow;                           /* what the store holds */

/* receiver, driven one byte at a time */
static uint8_t      g_stage       = 0U;                 /* 0 hunt, 1 sof1, 2 len, 3 func, 4 payload */
static uint8_t      g_declared    = 0U;
static uint8_t      g_fid         = 0U;
static uint8_t      g_need        = 0U;
static uint8_t      g_got         = 0U;
static uint8_t      g_payload[RX_CAP];
static uint32_t     g_last_rx     = 0U;

/* ------------------------------------------------------------ panel lines */

static void note_set(const char *s)
{
    uint8_t i = 0U;

    while ((i < PANEL_COLS) && (s[i] != '\0'))
    {
        g_note[i] = s[i];
        i++;
    }
    while (i < PANEL_COLS)
    {
        g_note[i] = ' ';
        i++;
    }
    g_note[PANEL_COLS] = '\0';
}

static void text_space(void)
{
    uint32_t i;

    for (i = 0U; i < NV_TEXT_LEN; i++)
    {
        g_text[i] = ' ';
    }
    g_nchars = 0U;
}

static void panel_show(void)
{
    char    line[PANEL_COLS + 1U];
    uint8_t i;

    line[0]  = (g_from_nv != 0U) ? 'R' : 'N';
    line[1]  = ' ';
    line[2]  = 'L';
    line[3]  = ((g_state & NV_BIT_LEFT)  != 0U) ? '1' : '0';
    line[4]  = ' ';
    line[5]  = 'R';
    line[6]  = ((g_state & NV_BIT_RIGHT) != 0U) ? '1' : '0';
    line[7]  = ' ';
    line[8]  = 'B';
    line[9]  = ((g_state & NV_BIT_BEEP)  != 0U) ? '1' : '0';
    line[10] = ' ';
    line[11] = 'D';
    line[12] = ((g_state & NV_BIT_STRIP) != 0U) ? '1' : '0';
    line[13] = '\0';

    panel_blank_row(0U);
    panel_puts(0U, 0U, line);

    panel_blank_row(1U);
    panel_blank_row(2U);
    for (i = 0U; i < PANEL_COLS; i++)
    {
        panel_putc(i, 1U, g_text[i]);
        panel_putc(i, 2U, g_text[PANEL_COLS + i]);
    }

    panel_blank_row(3U);
    panel_puts(0U, 3U, g_note);

    panel_flush();
}

/* -------------------------------------------------------------- actuators */

static void drive_outputs(void)
{
    board_led_write(BOARD_LED_LEFT,  (uint8_t)((g_state & NV_BIT_LEFT)  != 0U));
    board_led_write(BOARD_LED_RIGHT, (uint8_t)((g_state & NV_BIT_RIGHT) != 0U));
    board_beep_write((uint8_t)((g_state & NV_BIT_BEEP) != 0U));
    board_rgb_write(((g_state & NV_BIT_STRIP) != 0U) ? BOARD_RGB_MASK : 0U);

    if ((g_state & (NV_BIT_LEFT | NV_BIT_RIGHT)) != 0U)
    {
        g_blink_phase = 1U;                 /* light up without waiting */
        g_blink_at    = tick_ms();
    }
}

static void blink_service(void)
{
    uint32_t now = tick_ms();
    uint8_t  on;

    if ((g_state & (NV_BIT_LEFT | NV_BIT_RIGHT)) == 0U)
    {
        g_blink_at = now;
        return;
    }
    if ((uint32_t)(now - g_blink_at) < BLINK_HALF_MS)
    {
        return;
    }

    g_blink_at     = now;
    g_blink_phase ^= 1U;
    on             = g_blink_phase;

    board_led_write(BOARD_LED_LEFT,
                    (uint8_t)(((g_state & NV_BIT_LEFT) != 0U) ? on : 0U));
    board_led_write(BOARD_LED_RIGHT,
                    (uint8_t)(((g_state & NV_BIT_RIGHT) != 0U) ? on : 0U));
}

static void report(void)
{
    uint8_t i;

    uart_puts("STATE");
    for (i = 0U; i < ACTUATOR_COUNT; i++)
    {
        uart_puts(" ");
        uart_puts(g_actuators[i].label);
        uart_puts(((g_state & g_actuators[i].bit) != 0U) ? "=ON" : "=OFF");
    }
    uart_puts("\r\n");
}

/* --------------------------------------------------------------- nv store */

static void shadow_build(nv_block_t *blk)
{
    uint32_t i;

    blk->tag    = NV_TAG;
    blk->state  = g_state;
    blk->nchars = g_nchars;
    blk->sum    = 0U;
    blk->spare  = 0U;

    for (i = 0U; i < NV_TEXT_LEN; i++)
    {
        blk->text[i] = g_text[i];
    }
}

/* Skips the erase / program cycle when the store already holds this content. */
static uint8_t persist(void)
{
    nv_block_t blk;

    shadow_build(&blk);

    if ((g_shadow.tag == NV_TAG) && (nv_equal(&blk, &g_shadow) != 0U))
    {
        return 1U;
    }
    if (nv_write(&blk) != 0U)
    {
        g_shadow = blk;
        uart_puts("NV  : committed\r\n");
        return 1U;
    }

    uart_puts("NV  : write rejected\r\n");
    return 0U;
}

static void apply_block(const nv_block_t *blk)
{
    uint32_t i;

    g_state = blk->state;
    for (i = 0U; i < NV_TEXT_LEN; i++)
    {
        g_text[i] = blk->text[i];
    }
    g_nchars = (blk->nchars <= NV_TEXT_LEN) ? blk->nchars : NV_TEXT_LEN;

    drive_outputs();
}

/* --------------------------------------------------------- frame handlers */

static void on_actuator(uint8_t code)
{
    uint8_t i;
    uint8_t known = 0U;

    for (i = 0U; i < ACTUATOR_COUNT; i++)
    {
        if (g_actuators[i].code == code)
        {
            g_state ^= g_actuators[i].bit;
            known = 1U;
            break;
        }
    }

    if (known == 0U)
    {
        note_set("BAD ACT CODE");
        uart_puts("ERR : unknown actuator code\r\n");
        panel_show();
        return;
    }

    drive_outputs();
    note_set((persist() != 0U) ? "ACT OK" : "NV WRITE ERR");
    report();
    panel_show();
}

static void on_text(void)
{
    char    echo[NV_TEXT_LEN + 1U];
    uint8_t n = g_got;
    uint8_t i;

    if (n > NV_TEXT_LEN)
    {
        n = (uint8_t)NV_TEXT_LEN;
    }

    for (i = 0U; i < n; i++)
    {
        uint8_t raw = g_payload[i];
        /* Anything outside the printable range would show up as junk. */
        g_text[i] = ((raw >= 0x20U) && (raw <= 0x7EU)) ? (char)raw : '.';
        echo[i]   = g_text[i];
    }
    echo[n] = '\0';

    for (i = n; i < NV_TEXT_LEN; i++)
    {
        g_text[i] = ' ';
    }
    g_nchars = n;

    uart_puts("TEXT: ");
    uart_puts(echo);
    uart_puts("\r\n");

    note_set((persist() != 0U) ? "TEXT SAVED" : "NV WRITE ERR");
    panel_show();
}

static void on_nvram(uint8_t op)
{
    nv_block_t blk;

    switch (op)
    {
        case NVRAM_SAVE:
            shadow_build(&blk);
            if (nv_write(&blk) != 0U)
            {
                g_shadow = blk;
                note_set("NV COMMITTED");
                uart_puts("NV  : committed\r\n");
            }
            else
            {
                note_set("NV WRITE ERR");
                uart_puts("NV  : write rejected\r\n");
            }
            break;

        case NVRAM_CLEAR:
            nv_erase();
            g_shadow.tag = 0U;              /* force the next persist() to write */
            note_set("NV WIPED");
            uart_puts("NV  : wiped\r\n");
            break;

        case NVRAM_RELOAD:
            if (nv_read(&blk) != 0U)
            {
                apply_block(&blk);
                g_shadow = blk;
                note_set("NV RELOADED");
                uart_puts("NV  : reloaded\r\n");
            }
            else
            {
                note_set("NV EMPTY");
                uart_puts("NV  : no valid block\r\n");
            }
            break;

        default:
            note_set("BAD NV CODE");
            uart_puts("ERR : unknown store code\r\n");
            break;
    }

    report();
    panel_show();
}

/* -------------------------------------------------------------- receiver */

static void rx_reset(void)
{
    g_stage    = 0U;
    g_declared = 0U;
    g_fid      = 0U;
    g_need     = 0U;
    g_got      = 0U;
}

static void dispatch(void)
{
    switch (g_fid)
    {
        case FID_ACTUATOR:
            on_actuator(g_payload[0]);
            break;

        case FID_TEXT:
            on_text();
            break;

        case FID_NVRAM:
            on_nvram(g_payload[0]);
            break;

        default:
            note_set("BAD FUNC ID");
            uart_puts("ERR : unknown function id\r\n");
            panel_show();
            break;
    }
}

/* Stage counter rather than a state enum: 0 hunt, 1 second SOF, 2 length,
   3 function id, 4 payload. */
static void rx_feed(uint8_t b)
{
    uint32_t now = tick_ms();

    if ((g_stage != 0U) && ((uint32_t)(now - g_last_rx) > RX_GAP_MS))
    {
        rx_reset();
    }
    g_last_rx = now;

    switch (g_stage)
    {
        case 0U:
            if (b == SOF0)
            {
                g_stage = 1U;
            }
            break;

        case 1U:
            if (b == SOF1)
            {
                g_stage = 2U;
            }
            else if (b == SOF0)
            {
                g_stage = 1U;               /* a run of 0x55 must not break the hunt */
            }
            else
            {
                rx_reset();
            }
            break;

        case 2U:
            if (b == 0U)
            {
                rx_reset();                 /* length must at least cover the id */
            }
            else
            {
                g_declared = b;
                g_stage    = 3U;
            }
            break;

        case 3U:
            g_fid  = b;
            g_got  = 0U;
            g_need = (b == FID_TEXT)
                   ? (uint8_t)((g_declared > 1U) ? (g_declared - 1U) : 0U)
                   : 1U;

            if (g_need == 0U)
            {
                dispatch();
                rx_reset();
            }
            else if (g_need > RX_CAP)
            {
                note_set("FRAME TOO LONG");
                panel_show();
                rx_reset();
            }
            else
            {
                g_stage = 4U;
            }
            break;

        case 4U:
            g_payload[g_got] = b;
            g_got++;
            g_need--;
            if (g_need == 0U)
            {
                dispatch();
                rx_reset();
            }
            break;

        default:
            rx_reset();
            break;
    }
}

/* ------------------------------------------------------------------- main */

int main(void)
{
    char       ch;
    nv_block_t blk;

    board_gpio_init();
    tick_init();
    panel_init();
    uart_init(UART_BAUD_RATE);

    text_space();
    note_set("BOOTING");
    panel_show();

    uart_puts("\r\n### serial panel node ###\r\n");
    uart_puts("act : 55 FF 03 06 <00 left|01 right|02 beep|03 strip>\r\n");
    uart_puts("text: 55 FF <n> 07 <bytes>      (n = 1 + char count)\r\n");
    uart_puts("nv  : 55 FF 02 08 <00 save|01 wipe|02 reload>\r\n");

    /* Power cycle recovery: the flash block wins over the reset defaults. */
    if (nv_read(&blk) != 0U)
    {
        apply_block(&blk);
        g_shadow  = blk;
        g_from_nv = 1U;
        note_set("NV DATA LOADED");
        uart_puts("BOOT: flash block applied\r\n");
    }
    else
    {
        g_shadow.tag = 0U;
        g_from_nv    = 0U;
        note_set("NV EMPTY");
        uart_puts("BOOT: flash empty, defaults in use\r\n");
    }

    drive_outputs();
    report();
    panel_show();

    while (1)
    {
        while (uart_getc(&ch) != 0U)
        {
            rx_feed((uint8_t)ch);
        }
        blink_service();
    }
}

/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   Host controlled indicators / buzzer demo.
  *
  *          Frame layout (fixed length, last byte is a reserved checksum slot):
  *              0x55 | 0xFF | 0x03 | 0x06 | <action> | [reserved]
  *
  *          <action>  0x00 -> left turn indicator (PG14)
  *                    0x01 -> right turn indicator (PG15)
  *                    0x02 -> buzzer on port PG12
  *                    0x03 -> LED strip on PG0/PG1/PG2
  *
  *          Each accepted frame toggles the addressed output, while a status
  *          line is sent back so the terminal shows what the board is doing.
  ******************************************************************************
  */

#include "board.h"
#include "tick.h"
#include "uart.h"

/* ---------------- frame layout ---------------- */
#define FRAME_SYNC_LEN      4U          /* 0x55 0xFF 0x03 0x06 */
#define FRAME_BODY_LEN      2U          /* action byte + reserved byte */

#define ACT_LEFT_TURN       0x00U
#define ACT_RIGHT_TURN      0x01U
#define ACT_BUZZER          0x02U
#define ACT_LED_STRIP       0x03U

/* ---------------- device state bits ---------------- */
#define ST_LEFT_TURN        (1U << 0)
#define ST_RIGHT_TURN       (1U << 1)
#define ST_BUZZER           (1U << 2)
#define ST_LED_STRIP        (1U << 3)

/* ---------------- timing ---------------- */
#define BLINK_HALF_MS       500U        /* a turn indicator flips every 500 ms */
#define FRAME_GAP_MS        200U        /* gap that discards a half frame      */

typedef struct
{
    uint8_t     bit;
    uint8_t     code;
    const char *name;
} action_item_t;

static const action_item_t actions[] =
{
    { ST_LEFT_TURN,  ACT_LEFT_TURN,  "LEFT_TURN"  },
    { ST_RIGHT_TURN, ACT_RIGHT_TURN, "RIGHT_TURN" },
    { ST_BUZZER,     ACT_BUZZER,     "BUZZER"     },
    { ST_LED_STRIP,  ACT_LED_STRIP,  "LED_STRIP"  }
};

#define ACTION_COUNT        (sizeof(actions) / sizeof(actions[0]))

static const uint8_t frame_sync[FRAME_SYNC_LEN] = { 0x55U, 0xFFU, 0x03U, 0x06U };

static uint8_t  state_bits  = 0U;
static uint8_t  blink_phase = 0U;
static uint32_t blink_stamp = 0U;

static uint8_t  frame_phase  = 0U;      /* index into the fixed header     */
static uint32_t frame_stamp  = 0U;

/* ====================== status reporting ====================== */
static void report_state(void)
{
    uint8_t i;

    uart_puts("BOARD");
    for (i = 0U; i < ACTION_COUNT; i++)
    {
        uart_puts(" ");
        uart_puts(actions[i].name);
        uart_puts(((state_bits & actions[i].bit) != 0U) ? "=ON" : "=OFF");
    }
    uart_puts("\r\n");
}

/* ====================== command execution ====================== */
static void execute_action(uint8_t code)
{
    uint8_t  on;
    uint32_t now = tick_ms();

    switch (code)
    {
        case ACT_LEFT_TURN:
            state_bits ^= ST_LEFT_TURN;
            on = (uint8_t)((state_bits & ST_LEFT_TURN) != 0U);
            board_led_write(BOARD_LED_LEFT, on);
            if (on != 0U)
            {
                blink_phase = 1U;       /* light up right away */
                blink_stamp = now;
            }
            break;

        case ACT_RIGHT_TURN:
            state_bits ^= ST_RIGHT_TURN;
            on = (uint8_t)((state_bits & ST_RIGHT_TURN) != 0U);
            board_led_write(BOARD_LED_RIGHT, on);
            if (on != 0U)
            {
                blink_phase = 1U;
                blink_stamp = now;
            }
            break;

        case ACT_BUZZER:
            state_bits ^= ST_BUZZER;
            board_beep_write((uint8_t)((state_bits & ST_BUZZER) != 0U));
            break;

        case ACT_LED_STRIP:
            state_bits ^= ST_LED_STRIP;
            board_rgb_write((state_bits & ST_LED_STRIP) ? BOARD_RGB_MASK : 0U);
            break;

        default:
            uart_puts("ERR unknown action\r\n");
            return;
    }

    report_state();
}

/* ====================== background tasks ====================== */
static void service_blink(void)
{
    uint32_t now = tick_ms();
    uint8_t  on;

    if ((state_bits & (ST_LEFT_TURN | ST_RIGHT_TURN)) == 0U)
    {
        blink_stamp = now;              /* idle, keep the stamp fresh */
        return;
    }

    if ((uint32_t)(now - blink_stamp) < BLINK_HALF_MS)
    {
        return;
    }

    blink_stamp = now;
    blink_phase ^= 1U;
    on           = blink_phase;

    board_led_write(BOARD_LED_LEFT,
                    (uint8_t)(((state_bits & ST_LEFT_TURN) != 0U) ? on : 0U));
    board_led_write(BOARD_LED_RIGHT,
                    (uint8_t)(((state_bits & ST_RIGHT_TURN) != 0U) ? on : 0U));
}

/* ====================== frame parser ====================== */
static void frame_feed(uint8_t byte)
{
    uint32_t now = tick_ms();

    if ((frame_phase != 0U) && ((uint32_t)(now - frame_stamp) > FRAME_GAP_MS))
    {
        frame_phase = 0U;               /* the frame stalled, start over */
    }
    frame_stamp = now;

    if (frame_phase < FRAME_SYNC_LEN)
    {
        if (byte == frame_sync[frame_phase])
        {
            frame_phase++;
        }
        else
        {
            /* a stray 0x55 may already open the next frame */
            frame_phase = (uint8_t)((byte == frame_sync[0]) ? 1U : 0U);
        }
        return;
    }

    if (frame_phase == FRAME_SYNC_LEN)
    {
        execute_action(byte);
        frame_phase = (uint8_t)(FRAME_SYNC_LEN + 1U);
        return;
    }

    /* trailing reserved byte: swallowed, but it may hide a new header */
    frame_phase = (uint8_t)((byte == frame_sync[0]) ? 1U : 0U);
}

/* ====================== entry point ====================== */
int main(void)
{
    char rx_byte;

    board_gpio_init();
    tick_init();
    uart_init(UART_BAUD_RATE);

    uart_puts("\r\n### serial control board ready ###\r\n");
    uart_puts("frame  55 FF 03 06 AA | AA = 00 left, 01 right, 02 buzzer, 03 led\r\n");

    while (1)
    {
        while (uart_getc(&rx_byte) != 0U)
        {
            frame_feed((uint8_t)rx_byte);
        }
        service_blink();
    }
}

// Task 2 - key drives an LED, with two RGB groups (color + blink)
// STM32F103ZET6, ST standard peripheral library
#include "stm32f10x.h"

/* ----- on-board resources (YB-DSF01 board) ----- */
#define LED1  GPIO_Pin_14
#define LED2  GPIO_Pin_15
#define KEY1  GPIO_Pin_3
#define KEY2  GPIO_Pin_4
#define KEY3  GPIO_Pin_5

/* RGB group1 = PG0/1/2, group2 = PE2/3/4 ; common-cathode (high level = on) */

/* 8 colors packed as 3 bits: b2=R b1=G b0=B */
static const uint8_t COLOR[8] = {
    0x0, /* off    */
    0x4, /* red    */
    0x2, /* green  */
    0x1, /* blue   */
    0x6, /* yellow */
    0x5, /* magenta*/
    0x3, /* cyan   */
    0x7  /* white  */
};

static uint8_t  colorIdx = 0;   /* index 0..7 */
static uint8_t  mode     = 0;   /* 0 static / 1 all-blink / 2 group-alternate */
static uint32_t frame    = 0;

static void delay(uint32_t n)
{
    for (volatile uint32_t i = 0; i < n; i++);
}

static void gpioInit(void)
{
    GPIO_InitTypeDef g;
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG | RCC_APB2Periph_GPIOE, ENABLE);

    g.GPIO_Mode  = GPIO_Mode_Out_PP;
    g.GPIO_Speed = GPIO_Speed_50MHz;
    g.GPIO_Pin   = GPIO_Pin_0 | GPIO_Pin_1 | GPIO_Pin_2;
    GPIO_Init(GPIOG, &g);                       /* RGB group1 */
    g.GPIO_Pin   = GPIO_Pin_2 | GPIO_Pin_3 | GPIO_Pin_4;
    GPIO_Init(GPIOE, &g);                       /* RGB group2 */
    g.GPIO_Pin   = LED1 | LED2;
    GPIO_Init(GPIOG, &g);                       /* basic LEDs */
    g.GPIO_Mode  = GPIO_Mode_IN_FLOATING;
    g.GPIO_Pin   = KEY1 | KEY2 | KEY3;
    GPIO_Init(GPIOG, &g);                       /* keys */
}

/* write one RGB group from a packed 3-bit color */
static void rgbSet(GPIO_TypeDef* port, uint16_t rpin, uint16_t gpin, uint16_t bpin, uint8_t c)
{
    GPIO_WriteBit(port, rpin, (c & 0x4) ? Bit_SET : Bit_RESET);
    GPIO_WriteBit(port, gpin, (c & 0x2) ? Bit_SET : Bit_RESET);
    GPIO_WriteBit(port, bpin, (c & 0x1) ? Bit_SET : Bit_RESET);
}

static void rgbDrive(uint8_t g1, uint8_t g2)
{
    rgbSet(GPIOG, GPIO_Pin_0, GPIO_Pin_1, GPIO_Pin_2, g1);
    rgbSet(GPIOE, GPIO_Pin_2, GPIO_Pin_3, GPIO_Pin_4, g2);
}

/* rising-edge detect, previous level kept by caller */
static uint8_t edge(GPIO_TypeDef* port, uint16_t pin, uint8_t* st)
{
    uint8_t now = (GPIO_ReadInputDataBit(port, pin) == Bit_SET);
    uint8_t hit = now && !(*st);
    *st = now;
    return hit;
}

int main(void)
{
    uint8_t k2 = 0, k3 = 0;
    gpioInit();

    for (;;) {
        /* original task2: KEY1 holds LED1 on while pressed */
        GPIO_WriteBit(GPIOG, LED1,
            (GPIO_ReadInputDataBit(GPIOG, KEY1) == Bit_SET) ? Bit_SET : Bit_RESET);

        if (edge(GPIOG, KEY2, &k2)) colorIdx = (colorIdx + 1) & 7;
        if (edge(GPIOG, KEY3, &k3)) mode = (mode + 1) % 3;

        uint8_t c = COLOR[colorIdx];
        uint8_t phase = (frame >> 4) & 1;        /* flip every 16 frames */

        switch (mode) {
        case 0:  /* static */
            rgbDrive(c, c);
            GPIO_ResetBits(GPIOG, LED2);
            break;
        case 1:  /* both groups blink together, LED2 mirrors */
            if (phase) { rgbDrive(c, c); GPIO_SetBits(GPIOG, LED2); }
            else      { rgbDrive(0, 0); GPIO_ResetBits(GPIOG, LED2); }
            break;
        default: /* alternate groups */
            if (phase) { rgbDrive(c, 0); GPIO_SetBits(GPIOG, LED2); }
            else      { rgbDrive(0, c); GPIO_ResetBits(GPIOG, LED2); }
            break;
        }

        delay(0x3FFFF);
        frame++;
    }
}

/**
  ******************************************************************************
  * @file    Drv_Common/uart.c
  * @brief   Register level USART1 driver: 8 data bits, 1 stop bit, no parity.
  *          TX waits on TXE, RX drains DR inside the USART1 interrupt.
  ******************************************************************************
  */

#include "uart.h"
#include "stm32f10x.h"

#define RX_INDEX_MASK       (UART_RX_BUF_LEN - 1U)

/* PA9 -> CNF = 10 (alternate function push-pull), MODE = 11 (50 MHz) */
#define PA9_CRH_NIBBLE      0xBU
/* PA10 -> CNF = 01 (floating input), MODE = 00 */
#define PA10_CRH_NIBBLE     0x4U

static volatile uint8_t  rx_buf[UART_RX_BUF_LEN];
static volatile uint16_t rx_wr = 0U;
static volatile uint16_t rx_rd = 0U;

void uart_init(uint32_t baud)
{
    uint32_t crh;

    /* Port A and USART1 live on APB2 */
    RCC->APB2ENR |= RCC_APB2ENR_IOPAEN | RCC_APB2ENR_USART1EN;

    /* PA9 / PA10 alternate function and input configuration */
    crh  = GPIOA->CRH;
    crh &= ~((0xFU << 4) | (0xFU << 8));
    crh |=  ((uint32_t)PA9_CRH_NIBBLE << 4) | ((uint32_t)PA10_CRH_NIBBLE << 8);
    GPIOA->CRH = crh;

    /* Baud rate: APB2 runs at the core clock, BRR holds the division */
    USART1->BRR = (SystemCoreClock + (baud / 2U)) / baud;

    USART1->CR1 = USART_CR1_UE   |      /* USART enable                  */
                  USART_CR1_TE   |      /* transmitter enable            */
                  USART_CR1_RE   |      /* receiver enable               */
                  USART_CR1_RXNEIE;     /* receive not empty interrupt   */

    /* Enable the USART1 line in the NVIC (IRQ 37 -> ISER bit 5) */
    NVIC->ISER[(uint32_t)USART1_IRQn >> 5U] |=
        (uint32_t)(1UL << ((uint32_t)USART1_IRQn & 0x1FU));
}

void uart_putc(char c)
{
    while ((USART1->SR & USART_SR_TXE) == 0U)
    {
        /* wait until the transmit register can take a new byte */
    }
    USART1->DR = (uint16_t)c;
}

void uart_puts(const char *s)
{
    if (s == 0)
    {
        return;
    }
    while (*s != '\0')
    {
        uart_putc(*s);
        s++;
    }
}

uint8_t uart_getc(char *pch)
{
    if ((pch == 0) || (rx_wr == rx_rd))
    {
        return 0U;
    }

    *pch = (char)rx_buf[rx_rd];
    rx_rd = (uint16_t)((rx_rd + 1U) & RX_INDEX_MASK);
    return 1U;
}

/* One byte in, one byte stored; a full buffer simply drops the new byte. */
void USART1_IRQHandler(void)
{
    if ((USART1->SR & USART_SR_RXNE) != 0U)
    {
        uint8_t  data = (uint8_t)USART1->DR;
        uint16_t next = (uint16_t)((rx_wr + 1U) & RX_INDEX_MASK);

        if (next != rx_rd)
        {
            rx_buf[rx_wr] = data;
            rx_wr = next;
        }
    }
}

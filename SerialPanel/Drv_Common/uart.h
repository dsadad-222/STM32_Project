/**
  ******************************************************************************
  * @file    Drv_Common/uart.h
  * @brief   USART1 console port on PA9 (TX) and PA10 (RX).
  *          Reception is interrupt driven into a small ring buffer.
  ******************************************************************************
  */

#ifndef UART_H
#define UART_H

#include <stdint.h>

#define UART_BAUD_RATE      115200U
#define UART_RX_BUF_LEN     64U

void    uart_init(uint32_t baud);
void    uart_putc(char c);
void    uart_puts(const char *s);

/* Returns 1 and stores one byte when data is available, 0 when empty. */
uint8_t uart_getc(char *pch);

#endif /* UART_H */

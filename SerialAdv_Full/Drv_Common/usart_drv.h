/**
  ******************************************************************************
  * @file    Drv_Common/usart_drv.h
  * @brief   串口驱动（USART1：PA9 = TX，PA10 = RX）
  *          接收采用"中断 + 环形缓冲"，主循环里轮询取字节，不阻塞
  ******************************************************************************
  */

#ifndef __USART_DRV_H
#define __USART_DRV_H

#include "stm32f10x.h"

/* 串口参数：PC 串口助手按这个配置打开（8 位数据、1 位停止、无校验） */
#define USART_BAUD_DEFAULT      115200
#define USART_RX_BUFFER_SIZE    64      /* 接收环形缓冲深度，必须是 2 的幂 */

void    Usart_Init(uint32_t baud);
void    Usart_SendByte(uint8_t byte);
void    Usart_SendString(const char *str);

/* 从接收缓冲取一个字节：返回 1 = 取到一字节，返回 0 = 缓冲为空 */
uint8_t Usart_ReadByte(uint8_t *pByte);

#endif /* __USART_DRV_H */

/**
  ******************************************************************************
  * @file    Drv_Common/usart_drv.c
  * @brief   串口驱动实现（USART1，115200-8-N-1）
  *          TX 配置为复用推挽输出，RX 配置为浮空/上拉输入，接收中断进环形缓冲
  ******************************************************************************
  */

#include "usart_drv.h"

/* ---------------------------------------------------------------- 环形缓冲 */
#define RX_BUF_MASK     (USART_RX_BUFFER_SIZE - 1)

static volatile uint8_t  s_rxBuffer[USART_RX_BUFFER_SIZE];
static volatile uint16_t s_rxHead = 0;      /* 中断里写 */
static volatile uint16_t s_rxTail = 0;      /* 主循环里读 */

/* ---------------------------------------------------------------- 初始化 */
void Usart_Init(uint32_t baud)
{
    GPIO_InitTypeDef  GPIO_InitStructure;
    USART_InitTypeDef USART_InitStructure;
    NVIC_InitTypeDef  NVIC_InitStructure;

    /* USART1 与 PA9/PA10 都挂在 APB2 上 */
    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOA | RCC_APB2Periph_USART1, ENABLE);

    /* PA9  -> USART1_TX，复用推挽输出 */
    GPIO_InitStructure.GPIO_Pin   = GPIO_Pin_9;
    GPIO_InitStructure.GPIO_Mode  = GPIO_Mode_AF_PP;
    GPIO_InitStructure.GPIO_Speed = GPIO_Speed_50MHz;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    /* PA10 -> USART1_RX，浮空输入（板上有 USB 转串口芯片驱动） */
    GPIO_InitStructure.GPIO_Pin  = GPIO_Pin_10;
    GPIO_InitStructure.GPIO_Mode = GPIO_Mode_IN_FLOATING;
    GPIO_Init(GPIOA, &GPIO_InitStructure);

    USART_InitStructure.USART_BaudRate            = baud;
    USART_InitStructure.USART_WordLength          = USART_WordLength_8b;
    USART_InitStructure.USART_StopBits            = USART_StopBits_1;
    USART_InitStructure.USART_Parity              = USART_Parity_No;
    USART_InitStructure.USART_HardwareFlowControl = USART_HardwareFlowControl_None;
    USART_InitStructure.USART_Mode                = USART_Mode_Rx | USART_Mode_Tx;
    USART_Init(USART1, &USART_InitStructure);

    /* 接收不为空中断：每来一个字节进一次 USART1_IRQHandler */
    USART_ITConfig(USART1, USART_IT_RXNE, ENABLE);

    NVIC_InitStructure.NVIC_IRQChannel                   = USART1_IRQn;
    NVIC_InitStructure.NVIC_IRQChannelPreemptionPriority = 1;
    NVIC_InitStructure.NVIC_IRQChannelSubPriority        = 1;
    NVIC_InitStructure.NVIC_IRQChannelCmd                = ENABLE;
    NVIC_Init(&NVIC_InitStructure);

    USART_Cmd(USART1, ENABLE);
}

/* ---------------------------------------------------------------- 发送 */
void Usart_SendByte(uint8_t byte)
{
    while (USART_GetFlagStatus(USART1, USART_FLAG_TXE) == RESET)
    {
        /* 等发送数据寄存器空 */
    }
    USART_SendData(USART1, byte);
}

void Usart_SendString(const char *str)
{
    if (str == 0)
    {
        return;
    }
    while (*str != '\0')
    {
        Usart_SendByte((uint8_t)(*str));
        str++;
    }
}

/* ---------------------------------------------------------------- 接收 */
/* 主循环里调用：取到返回 1，缓冲空返回 0 */
uint8_t Usart_ReadByte(uint8_t *pByte)
{
    if (pByte == 0)
    {
        return 0;
    }
    if (s_rxHead == s_rxTail)
    {
        return 0;                       /* 空 */
    }
    *pByte    = s_rxBuffer[s_rxTail];
    s_rxTail  = (uint16_t)((s_rxTail + 1) & RX_BUF_MASK);
    return 1;
}

/* ---------------------------------------------------------------- 中断 */
void USART1_IRQHandler(void)
{
    if (USART_GetITStatus(USART1, USART_IT_RXNE) != RESET)
    {
        uint16_t next = (uint16_t)((s_rxHead + 1) & RX_BUF_MASK);

        /* 缓冲没满才存，满了就丢弃（保证不覆盖未读数据） */
        if (next != s_rxTail)
        {
            s_rxBuffer[s_rxHead] = (uint8_t)USART_ReceiveData(USART1);
            s_rxHead             = next;
        }
        else
        {
            (void)USART_ReceiveData(USART1);
        }

        USART_ClearITPendingBit(USART1, USART_IT_RXNE);
    }
}

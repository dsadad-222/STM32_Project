#include "drv_led.h"
#include "stm32f10x.h"

/* 单个 LED 的硬件资源描述 (时钟 + 端口 + 引脚) */
typedef struct {
    uint32_t      rcc_Periph;
    GPIO_TypeDef *gpio;
    uint16_t      pin;
} LED_GPIO_t;

/* 引脚映射表 (与原理图 net label 对应)
 *   LED1/LED2 -> PG14/PG15
 *   LRGB_R/G/B -> PG0/PG1/PG2
 *   RRGB_R/G/B -> PE2/PE3/PE4
 * 高电平点亮 (共阴)
 */
static const LED_GPIO_t led_map[] = {
    [LED1]   = { RCC_APB2Periph_GPIOG, GPIOG, GPIO_Pin_14 },
    [LED2]   = { RCC_APB2Periph_GPIOG, GPIOG, GPIO_Pin_15 },
    [LRGB_R] = { RCC_APB2Periph_GPIOG, GPIOG, GPIO_Pin_0  },
    [LRGB_G] = { RCC_APB2Periph_GPIOG, GPIOG, GPIO_Pin_1  },
    [LRGB_B] = { RCC_APB2Periph_GPIOG, GPIOG, GPIO_Pin_2  },
    [RRGB_R] = { RCC_APB2Periph_GPIOE, GPIOE, GPIO_Pin_2  },
    [RRGB_G] = { RCC_APB2Periph_GPIOE, GPIOE, GPIO_Pin_3  },
    [RRGB_B] = { RCC_APB2Periph_GPIOE, GPIOE, GPIO_Pin_4  },
};

void Led_Drv_Init(void)
{
    GPIO_InitTypeDef gpio;
    gpio.GPIO_Mode  = GPIO_Mode_Out_PP;
    gpio.GPIO_Speed = GPIO_Speed_50MHz;

    RCC_APB2PeriphClockCmd(RCC_APB2Periph_GPIOG | RCC_APB2Periph_GPIOE, ENABLE);

    for (uint32_t i = 0; i < sizeof(led_map) / sizeof(led_map[0]); ++i) {
        gpio.GPIO_Pin = led_map[i].pin;
        GPIO_Init(led_map[i].gpio, &gpio);
    }
}

void Led_On(LED_NO_t ledno)
{
    GPIO_SetBits(led_map[ledno].gpio, led_map[ledno].pin);
}

void Led_Off(LED_NO_t ledno)
{
    GPIO_ResetBits(led_map[ledno].gpio, led_map[ledno].pin);
}

void Led_Toggle(LED_NO_t ledno)
{
    GPIO_TypeDef *port = led_map[ledno].gpio;
    uint16_t      pin  = led_map[ledno].pin;

    if (GPIO_ReadOutputDataBit(port, pin) == Bit_SET) {
        GPIO_ResetBits(port, pin);
    } else {
        GPIO_SetBits(port, pin);
    }
}

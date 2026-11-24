/**
  ******************************************************************************
  * @file    Drv_Common/adc_drv.h
  * @brief   ADC 驱动：采集芯片内部温度传感器，并换算成电压与温度
  *
  *          一、温度传感器接在哪个通道？
  *              STM32F103 把温度传感器和内部参考电压做在芯片里面，出厂就接好了：
  *                  通道 16 (ADC_Channel_16) = 内部温度传感器
  *                  通道 17 (ADC_Channel_17) = 内部参考电压 Vrefint（典型 1.20V）
  *              通道 16/17 属于"内部通道"，只有 **ADC1** 能选它们，ADC2/ADC3 选不到；
  *              而且必须把 ADC_CR2 的 TSVREFE 位置 1（标准库函数
  *              ADC_TempSensorVrefintCmd(ENABLE)）才会把这两个内部通道接到转换器上，
  *              否则读回来永远是 0。
  *              在 ADC_SMPR1 里通道 16 属于 10~17 这一组，采样时间要按数据手册
  *              给足 17.1us 以上（见 adc_drv.c 里的 239.5 周期说明）。
  *
  *          二、换算公式（任务书给的典型值）
  *              Vsense(mV) = AD值 * VDDA / 4096
  *              温度(℃)   = (V25 - Vsense) / Avg_Slope + 25
  *              其中 V25 = 1.43V，Avg_Slope = 4.3mV/℃
  *              温度传感器是"负温度系数"：温度越高 Vsense 越小，所以 25℃ 时
  *              Vsense = 1.43V，高于 25℃ 时 (V25 - Vsense) 为正。
  *
  *          三、为了更准，这里多做了一件事：用内部基准反推真实 VDDA
  *              板上 3V3 未必正好 3.300V，直接按 3.3V 换算会有偏差。ADC1 的
  *              通道 17 是内部 1.20V 基准，用它反推真实 VDDA：
  *                  VDDA = 1.20V * 4096 / Vrefint原始值
  *              这样电压和温度都用"实测 VDDA"换算。
  *
  *              ★ 注意：VDDA 的合理区间要给得足够宽，这里配成 1800 ~ 4600mV。
  *                因为供电电压是可能偏离 3.3V 的（电池供电、或者 3V3 这路被
  *                别的电源倒灌抬高）。一旦实测值落在"合理区间"之外被当成坏点
  *                退回默认 3.300V，换算出来的温度就会整体错几十度。
  *                真正需要防的只是"读回 0 / 读回满量程"这种明显坏点，
  *                那一层单独由 raw 值判断。
  *
  *          四、一键标定（KEY / 串口 K 命令）
  *              即使公式和 VDDA 都对，每颗芯片的 V25、Avg_Slope 也有出厂离散性，
  *              理论值和实测值可能差好几度。所以再留一层"单点标定"：
  *              在一个已知温度（比如室温 25℃）下按一次 K，把当前读数标定成
  *              参考温度，得到的偏移量存进内部 Flash，掉电不丢。
  ******************************************************************************
  */

#ifndef __ADC_DRV_H
#define __ADC_DRV_H

#include "stm32f10x.h"

/* 内部通道（只有 ADC1 能选） */
#define ADC_TEMP_CHANNEL        ADC_Channel_16          /* 内部温度传感器 */
#define ADC_VREFINT_CHANNEL     ADC_Channel_17          /* 内部参考电压 1.20V */

#define ADC_AVG_TIMES           8u                      /* 内部通道噪声大，软件平均 8 次 */
#define ADC_FULL_SCALE          4096u                   /* 12 位 ADC：2^12 */

#define ADC_VDDA_MV_DEFAULT     3300u                   /* 兜底默认 3.30V */
#define ADC_VREFINT_MV          1200u                   /* Vrefint 典型值 1.20V */
#define ADC_VDDA_MV_MIN         1800u                   /* VDDA 合理区间下限（放宽，见文件头说明）*/
#define ADC_VDDA_MV_MAX         4600u                   /* VDDA 合理区间上限（放宽，见文件头说明）*/
#define ADC_VDDA_MV_WARN        3700u                   /* 超过这个值就串口告警：供电偏高 */
#define ADC_VREFINT_RAW_MIN     100u                    /* Vrefint 原始值下限：低于此视为坏点 */
#define ADC_VREFINT_RAW_MAX     4000u                   /* Vrefint 原始值上限：高于此视为坏点 */

#define ADC_V25_MV              1430                    /* V25 典型值 1.43V */
#define ADC_SLOPE_X10_UV_PER_C  43                      /* Avg_Slope 4.3mV/℃ = 43 (0.1mV/℃) */

/* 一键标定的默认参考温度：25.00℃（室温）*/
#define ADC_CAL_REF_X100        2500
#define ADC_CAL_OFFSET_X100_LIMIT  12000   /* 标定偏移量上限 ±120℃（超过就没有物理意义了）*/

/* 内部温度传感器数据手册给出的量程是 -40 ~ 125℃。
 * 如果算出来的温度跑到这个范围之外（比如 TSVREFE 没打开、通道读回 0，
 * 公式会算出 357℃ 这种离谱值），就把这次采样标记为无效，屏上显示 --，
 * 而不是把一个天文数字当真值报出去。*/
#define ADC_TEMP_X100_MIN       (-4000)                 /* -40.00℃ */
#define ADC_TEMP_X100_MAX       (12500)                 /* 125.00℃ */

/* 一次采样得到的一组数据 */
typedef struct
{
    uint16_t rawValue;      /* 温度通道 ADC 原始值（0 ~ 4095）*/
    uint16_t vrefRaw;       /* Vrefint 通道 ADC 原始值（诊断用，看它就知道 VDDA 反推是否可信）*/
    uint16_t vddaMv;        /* 本次换算用的 VDDA（mV）*/
    uint32_t voltageMv;     /* 换算后的模拟量（mV）*/
    int32_t  tempX100;      /* 温度 ×100（如 3052 表示 30.52℃），已含标定偏移 */
    uint8_t  valid;         /* 1 = 温度在传感器量程内，可信；0 = 超量程，显示 -- */
} AdcTempSample_t;

void     Adc_Init(void);
uint16_t Adc_ReadChannelAvg(uint8_t channel, uint8_t times);
uint16_t Adc_GetVddaMv(void);
uint32_t Adc_RawToVoltageMv(uint16_t raw, uint16_t vddaMv);
int32_t  Adc_RawToTempX100(uint16_t raw, uint16_t vddaMv);   /* 只按手册公式算，不含标定偏移 */

/* 单点标定偏移量（×100℃）。存进 Flash，掉电不丢 */
void     Adc_SetCalOffsetX100(int32_t offsetX100);
int32_t  Adc_GetCalOffsetX100(void);

void     Adc_SampleTemp(AdcTempSample_t *sample);

#endif /* __ADC_DRV_H */

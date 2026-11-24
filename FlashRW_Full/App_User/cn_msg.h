/**
  ******************************************************************************
  * @file    App_User/cn_msg.h
  * @brief   中文提示的 GBK 字节串（由 gen_cn_font.py 自动生成，请勿手改）
  *
  *          串口助手把编码设成 GBK/ANSI 就能直接看到这些汉字；
  *          OLED 显示时由 OLED_ShowCNString() 按 GBK 双字节查字库渲染。
  *
  *          全部写成 \xHH 转义，源码里不出现中文字节，
  *          这样无论 Keil 用什么源码编码编译，发出去的字节都一模一样。
  ******************************************************************************
  */

#ifndef __CN_MSG_H
#define __CN_MSG_H

#define CN_BOOT_OK       "\xCF\xB5\xCD\xB3\xC6\xF4\xB6\xAF\xCD\xEA\xB3\xC9"   /* 系统启动完成 */
#define CN_BOOTING       "\xD5\xFD\xD4\xDA\xC6\xF4\xB6\xAF"   /* 正在启动 */
#define CN_BOOT_FLASH    "\xB6\xC1\xC8\xA1\xB4\xE6\xB4\xA2"   /* 读取存储 */
#define CN_NO_FLASH      "\xCE\xDE\xB4\xE6\xB4\xA2\xCA\xFD\xBE\xDD"   /* 无存储数据 */
#define CN_CAL_OK        "\xB1\xEA\xB6\xA8\xCD\xEA\xB3\xC9"   /* 标定完成 */
#define CN_CAL_SKIP      "\xB6\xC1\xCA\xFD\xCE\xDE\xD0\xA7"   /* 读数无效 */
#define CN_CAL_CLEAR     "\xB1\xEA\xB6\xA8\xC7\xE5\xB3\xFD"   /* 标定清除 */
#define CN_FLASH_ERR     "\xB4\xE6\xB4\xA2\xCA\xA7\xB0\xDC"   /* 存储失败 */
#define CN_SAVED         "\xD2\xD1\xB1\xA3\xB4\xE6"   /* 已保存 */
#define CN_CLEARED       "\xD2\xD1\xC7\xE5\xB3\xFD"   /* 已清除 */
#define CN_CTRL_OK       "\xBF\xD8\xD6\xC6\xCD\xEA\xB3\xC9"   /* 控制完成 */
#define CN_BAD_CODE      "\xD6\xB8\xC1\xEE\xB4\xED\xCE\xF3"   /* 指令错误 */
#define CN_BREATH_ON     "\xBA\xF4\xCE\xFC\xBF\xAA"   /* 呼吸开 */
#define CN_BREATH_OFF    "\xBA\xF4\xCE\xFC\xB9\xD8"   /* 呼吸关 */
#define CN_TEMP          "\xCE\xC2\xB6\xC8"   /* 温度 */
#define CN_VDDA_WARN     "\xBE\xAF\xB8\xE6\xB9\xA9\xB5\xE7\xC6\xAB\xB8\xDF"   /* 警告供电偏高 */
/* ↓ 下面三个只在串口用（OLED 字库里没有这几个字，也无需加） */
#define CN_CAL_NONE      "\xCE\xC2\xB6\xC8\xCE\xB4\xB1\xEA\xB6\xA8"           /* 温度未标定 */
#define CN_CAL_HINT      "\xB7\xA2\x4B\xBC\xD3\xCA\xD2\xCE\xC2\xBB\xD8\xB3\xB5\xB1\xEA\xB6\xA8"   /* 发K加室温回车标定 */
#define CN_CAL_USE       "\xB1\xEA\xB6\xA8\xC9\xFA\xD0\xA7"                   /* 标定生效 */
/* ↓ 每次采样后那行中文摘要的词 */
#define CN_SUMMARY       "\xD0\xA1\xBD\xE1"                                   /* 小结 */
#define CN_VOLT          "\xB5\xE7\xD1\xB9"                                   /* 电压 */
#define CN_RAWVAL        "\xD4\xAD\xCA\xBC\xD6\xB5"                           /* 原始值 */
#define CN_DIE_TEMP      "\xD0\xBE\xC6\xAC\xBD\xE1\xCE\xC2"                   /* 芯片结温 */
#define CN_CALED         "\xD2\xD1\xB1\xEA\xB6\xA8"                           /* 已标定 */
#define CN_UNCAL         "\xCE\xB4\xB1\xEA\xB6\xA8"                           /* 未标定 */

#endif /* __CN_MSG_H */

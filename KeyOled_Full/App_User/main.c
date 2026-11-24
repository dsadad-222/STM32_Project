/**
  ******************************************************************************
  * @file    App_User/main.c
  * @brief   KEY1 + OLED 最小演示工程
  *
  *          功能（只有两个动作，故意做得很干净）：
  *              上电      -> OLED 居中显示「李登辉」
  *              按 KEY1   -> 切换成「叫爸爸」
  *              再按 KEY1 -> 切回「李登辉」
  *
  *          用到的外设只有两个：
  *              KEY1  -> PG3（上拉输入，按下为低电平）
  *              OLED  -> PB6 = SCL / PB7 = SDA（软件 I2C1，128x32 像素）
  *
  *          设计要点：
  *          1) 主循环不阻塞。用 SysTick 的 1ms 时基做"到点才扫"，
  *             每 KEY_SCAN_PERIOD_MS（10ms）调一次 Key_Scan，其余时间空转。
  *          2) 消抖放在驱动里（key_drv.c 内部 20ms），应用层拿到的
  *             已经是干净的单击事件，不用再写延时。
  *          3) 汉字用 GBK 双字节查 16x16 字库渲染，所以源码里全部写成
  *             \xHH 转义 —— 这样无论 Keil 用 GB2312 还是 UTF-8 存源码，
  *             编译出来的字节串都一模一样，不会出现"换台电脑就乱码"。
  *          4) 汉字是 16x16 的，屏只有 32 行高，一个字块跨 page 和 page+1
  *             两页。取 page = 1 时字块落在 y = 8~23，上下各留 8 行，
  *             在 32 行屏上正好垂直居中。
  ******************************************************************************
  */

#include "stm32f10x.h"

#include "oled_drv.h"
#include "key_drv.h"
#include "systick_drv.h"
#include "usart_drv.h"

/* ---------------------------------------------------------------------------
 * 两个界面各自的中文串（GBK 编码，全部用 \xHH 转义写死）
 * ------------------------------------------------------------------------- */
static const char CN_NAME[] = "\xC0\xEE\xB5\xC7\xBB\xD4";              /* 李登辉 */
static const char CN_CALL[] = "\xBD\xD0\xB0\xD6\xB0\xD6";              /* 叫爸爸 */

/* 汉字字块占 page 和 page+1 两页；屏共 4 页（0~3），
 * 取 1 则占用第 1、2 页 = y = 8~23，屏高 32 上下各空 8 行，垂直居中。 */
#define CN_PAGE_MID         1u

/* ---------------------------------------------------------------------------
 * 内部函数
 * ------------------------------------------------------------------------- */

/**
  * @brief  把一屏内容画上 OLED（先清显存，再居中写汉字，最后整屏刷新）
  * @param  cn  GBK 字节串，例如 CN_NAME / CN_CALL
  * @note   必须走 OLED_Clear + OLED_Refresh 这一对：
  *         OLED_Clear 只清显存不写屏，OLED_Refresh 才把显存整屏推到屏上。
  *         少了 Refresh，屏上还是上一屏的残影。
  */
static void Screen_Show(const char *cn)
{
    OLED_Clear();
    OLED_ShowCNStringCenter(CN_PAGE_MID, cn);
    OLED_Refresh();
}

/**
  * @brief  串口旁路提示（不影响功能，只为让串口助手能看见切换动作）
  * @param  showCall  1 = 当前在「叫爸爸」界面，0 = 在「李登辉」界面
  * @note   走的是纯 ASCII，串口助手不管设成什么编码都不会乱码。
  */
static void Log_State(uint8_t showCall)
{
    Usart_SendString("\r\n[KEY1] screen = ");
    Usart_SendString((showCall != 0u) ? "CALL" : "NAME");
    Usart_SendString("\r\n");
}

/* ---------------------------------------------------------------------------
 * 主函数
 * ------------------------------------------------------------------------- */
int main(void)
{
    uint8_t  showCall   = 0u;       /* 0 = 显示「李登辉」，1 = 显示「叫爸爸」*/
    uint32_t lastScanMs;            /* 上一次扫描按键的时刻 */

    /* ---- 1. 时基：必须最先初始化，后面所有"到点才做"都靠它 ---- */
    SysTick_Init();

    /* ---- 2. 串口：只做旁路监视，接不上也不影响 OLED 和按键 ---- */
    Usart_Init(USART_BAUD_DEFAULT);
    Usart_SendString("\r\n[BOOT] KeyOled_Full\r\n");

    /* ---- 3. 外设初始化 ---- */
    OLED_Init();
    Key_Init();

    /* ---- 4. 上电第一屏：李登辉 ---- */
    Screen_Show(CN_NAME);
    Log_State(showCall);

    lastScanMs = Get_SysRunTime();

    /* ---- 5. 主循环：到 10ms 才扫一次按键，其余时间空转 ---- */
    while (1)
    {
        if ((uint32_t)(Get_SysRunTime() - lastScanMs) >= KEY_SCAN_PERIOD_MS)
        {
            lastScanMs = Get_SysRunTime();

            /* 只认 KEY1 的单击；KEY2/KEY3 本工程不用，事件直接丢掉 */
            if (Key_Scan() == KEY_EVT_KEY1_CLICK)
            {
                showCall = (uint8_t)((showCall != 0u) ? 0u : 1u);    /* 两个界面来回切 */
                Screen_Show((showCall != 0u) ? CN_CALL : CN_NAME);
                Log_State(showCall);
            }
        }
    }
}

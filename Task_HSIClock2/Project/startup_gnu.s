    .syntax unified
    .cpu cortex-m3
    .thumb

    .section .isr_vector, "a"
    .word   0x20001000          /* Top of Stack */
    .word   Reset_Handler       /* Reset */
    .word   NMI_Handler
    .word   HardFault_Handler
    .word   MemManage_Handler
    .word   BusFault_Handler
    .word   UsageFault_Handler
    .word   0
    .word   0
    .word   0
    .word   0
    .word   SVC_Handler
    .word   DebugMon_Handler
    .word   0
    .word   PendSV_Handler
    .word   SysTick_Handler

    .text
    .thumb_func
    .type   Reset_Handler, %function
Reset_Handler:
    ldr     r0, =_estack
    mov     sp, r0
    /* 复制 .data 段 */
    ldr     r1, =_sidata
    ldr     r2, =_sdata
    ldr     r3, =_edata
1:
    cmp     r2, r3
    bge     2f
    ldr     r0, [r1], #4
    str     r0, [r2], #4
    b       1b
2:
    /* 清零 .bss 段 */
    ldr     r2, =_sbss
    ldr     r3, =_ebss
    mov     r0, #0
3:
    cmp     r2, r3
    bge     4f
    str     r0, [r2], #4
    b       3b
4:
    bl      SystemInit
    bl      main
    b       .

    .weak   NMI_Handler
    .type   NMI_Handler, %function
NMI_Handler:   b .
    .weak   HardFault_Handler
    .type   HardFault_Handler, %function
HardFault_Handler:   b .
    .weak   MemManage_Handler
    .type   MemManage_Handler, %function
MemManage_Handler:   b .
    .weak   BusFault_Handler
    .type   BusFault_Handler, %function
BusFault_Handler:   b .
    .weak   UsageFault_Handler
    .type   UsageFault_Handler, %function
UsageFault_Handler:   b .
    .weak   SVC_Handler
    .type   SVC_Handler, %function
SVC_Handler:   b .
    .weak   DebugMon_Handler
    .type   DebugMon_Handler, %function
DebugMon_Handler:   b .
    .weak   PendSV_Handler
    .type   PendSV_Handler, %function
PendSV_Handler:   b .
    .weak   SysTick_Handler
    .type   SysTick_Handler, %function
SysTick_Handler:   b .

    .end

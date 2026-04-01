/**
 * @file main.c
 * @brief Cortex-R5 safety demo — TMS570 bare-metal firmware
 *
 * Demonstrates R5-specific patterns that differ from Cortex-M:
 *   - RTI timer (not SysTick)
 *   - SCI UART (not generic USART)
 *   - DWD watchdog (RTI Digital Windowed Watchdog)
 *   - ESM status check (Error Signaling Module)
 *   - DCAN heartbeat (controller area network)
 *   - cpsid if / cpsie if (both IRQ + FIQ)
 *
 * Build: arm-none-eabi-gcc -mcpu=cortex-r5 -mfloat-abi=hard
 *        -mfpu=vfpv3-d16 -Os -T linker/tms570_app.ld -nostartfiles
 *        src/main.c src/r5_startup.c -o r5_safety_demo.elf
 */

#include "app_config.h"
#include <stdint.h>

/* ---- Register access ---- */
#define REG32(addr)  (*(volatile uint32_t *)(addr))

/* ---- SCI (UART) registers ---- */
#define SCI_GCR0     REG32(APP_SCI_BASE + 0x00)
#define SCI_GCR1     REG32(APP_SCI_BASE + 0x04)
#define SCI_BRS      REG32(APP_SCI_BASE + 0x2C)
#define SCI_FLR      REG32(APP_SCI_BASE + 0x1C)
#define SCI_TD       REG32(APP_SCI_BASE + 0x38)
#define SCI_RD       REG32(APP_SCI_BASE + 0x3C)

#define SCI_TXRDY    (1u << 8)
#define SCI_RXRDY    (1u << 9)

/* ---- RTI (Real-Time Interrupt) — DWD watchdog ---- */
#define RTI_DWDCTRL  REG32(APP_RTI_BASE + 0x90)
#define RTI_DWDPRLD  REG32(APP_RTI_BASE + 0x94)
#define RTI_WDSTATUS REG32(APP_RTI_BASE + 0x98)
#define RTI_WDKEY    REG32(APP_RTI_BASE + 0x9C)

/* ---- ESM (Error Signaling Module) ---- */
#define ESM_SR1      REG32(APP_ESM_BASE + 0x18)
#define ESM_SR4      REG32(APP_ESM_BASE + 0x58)
#define ESM_EKR      REG32(APP_ESM_BASE + 0x04)

/* ---- DCAN ---- */
#define DCAN_CTL     REG32(APP_DCAN_BASE + 0x00)
#define DCAN_IF1CMD  REG32(APP_DCAN_BASE + 0x40)
#define DCAN_IF1MSK  REG32(APP_DCAN_BASE + 0x44)
#define DCAN_IF1ARB  REG32(APP_DCAN_BASE + 0x48)
#define DCAN_IF1MCTL REG32(APP_DCAN_BASE + 0x4C)
#define DCAN_IF1DATA REG32(APP_DCAN_BASE + 0x50)

/* ---- GIO (GPIO) ---- */
#define GIO_DIR      REG32(APP_LED_PORT_BASE + 0x00)
#define GIO_DOUT     REG32(APP_LED_PORT_BASE + 0x04)

/* ---- Tick counter (incremented by RTI compare ISR) ---- */
static volatile uint32_t tick_ms;

void rti_compare0_handler(void)
{
    tick_ms++;
}

/* ---- SCI helpers ---- */

static void sci_init(void)
{
    SCI_GCR0 = 0;
    SCI_GCR0 = 1;
    SCI_GCR1 = (1u << 25) | (1u << 24) | (1u << 7) | (1u << 5);
    SCI_BRS  = (APP_CPU_HZ / (16 * APP_SCI_BAUD)) - 1;
}

static void sci_putc(char c)
{
    while (!(SCI_FLR & SCI_TXRDY)) {}
    SCI_TD = (uint32_t)c;
}

static void sci_puts(const char *s)
{
    while (*s) sci_putc(*s++);
}

static int sci_getc_timeout(uint32_t ms)
{
    uint32_t start = tick_ms;
    while (!(SCI_FLR & SCI_RXRDY)) {
        if ((tick_ms - start) >= ms) return -1;
    }
    return (int)(SCI_RD & 0xFF);
}

/* ---- DWD watchdog ---- */

static void dwd_init(void)
{
    RTI_DWDPRLD = APP_WDT_PRELOAD;
    RTI_DWDCTRL = 0xA98559DA;
}

static void dwd_feed(void)
{
    RTI_WDKEY = 0xE51A;
    RTI_WDKEY = 0xA35C;
}

/* ---- ESM check ---- */

static uint32_t esm_check_and_clear(void)
{
    uint32_t status = ESM_SR1;
    if (status) {
        ESM_SR1 = status;        /* W1C — clear flags */
        ESM_EKR = 0x00000005;    /* Reset error pin */
    }
    return status;
}

/* ---- DCAN heartbeat ---- */

static void dcan_init(void)
{
    DCAN_CTL = (1u << 0);           /* Init mode */
    DCAN_CTL = (1u << 6) | (1u << 5); /* CCE + DAR (disable auto-retransmit) */
    DCAN_CTL = 0;                   /* Normal operation */
}

static void dcan_send_heartbeat(uint32_t counter)
{
    DCAN_IF1ARB  = (1u << 29) | ((uint32_t)APP_CAN_NODE_ID << 18);
    DCAN_IF1MCTL = (1u << 8) | 4;  /* TxRqst + DLC=4 */
    DCAN_IF1DATA = counter;
    DCAN_IF1CMD  = (1u << 5) | 1;  /* Write to message object 1 */
}

/* ---- Interrupt helpers ---- */

static void irq_disable(void)
{
#if defined(__ARM_ARCH)
    __asm volatile ("cpsid if" ::: "memory");
#endif
}

static void irq_enable(void)
{
#if defined(__ARM_ARCH)
    __asm volatile ("cpsie if" ::: "memory");
#endif
}

/* ---- Main ---- */

int main(void)
{
    irq_disable();

    /* Initialize peripherals */
    sci_init();
    dwd_init();
    dcan_init();

    /* Configure LED GPIO */
    GIO_DIR |= (1u << APP_LED_BIT);

    /* Check ESM for latched errors from previous boot */
    uint32_t esm_flags = esm_check_and_clear();

    irq_enable();

    /* Boot banner */
    sci_puts("\r\n== Cortex-R5 Safety Demo ==\r\n");
    sci_puts("Board : TMS570LC43x\r\n");
    sci_puts("Core  : Cortex-R5F @ 300 MHz\r\n");
    if (esm_flags) {
        sci_puts("ESM   : errors cleared (0x");
        /* Minimal hex print */
        for (int i = 28; i >= 0; i -= 4) {
            uint32_t nib = (esm_flags >> i) & 0xF;
            sci_putc((char)(nib < 10 ? '0' + nib : 'A' + nib - 10));
        }
        sci_puts(")\r\n");
    } else {
        sci_puts("ESM   : clean\r\n");
    }
    sci_puts("Ready.\r\n");

    /* Main loop */
    uint32_t heartbeat_counter = 0;
    uint32_t last_heartbeat = 0;

    while (1) {
        /* Feed watchdog */
        dwd_feed();

        /* Echo received SCI byte */
        int ch = sci_getc_timeout(10);
        if (ch >= 0) {
            sci_putc((char)ch);
        }

        /* Periodic CAN heartbeat */
        if ((tick_ms - last_heartbeat) >= APP_HEARTBEAT_INTERVAL) {
            last_heartbeat = tick_ms;
            dcan_send_heartbeat(heartbeat_counter++);
            GIO_DOUT ^= (1u << APP_LED_BIT);
        }
    }

    return 0;
}

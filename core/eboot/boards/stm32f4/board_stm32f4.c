// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file board_stm32f4.c
 * @brief STM32F4 reference board port
 *
 * Reference HAL implementation for STM32F407. Uses direct register
 * access to avoid CMSIS/HAL library dependencies for portability.
 */

#include "board_stm32f4.h"
#include <string.h>

/* ---- STM32F4 Register Definitions ---- */

/* RCC */
#define RCC_BASE        0x40023800
#define RCC_CR          (*(volatile uint32_t *)(RCC_BASE + 0x00))
#define RCC_CFGR        (*(volatile uint32_t *)(RCC_BASE + 0x08))
#define RCC_AHB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x30))
#define RCC_APB1ENR     (*(volatile uint32_t *)(RCC_BASE + 0x40))

/* Flash interface */
#define FLASH_IF_BASE   0x40023C00
#define FLASH_ACR       (*(volatile uint32_t *)(FLASH_IF_BASE + 0x00))
#define FLASH_KEYR      (*(volatile uint32_t *)(FLASH_IF_BASE + 0x04))
#define FLASH_SR        (*(volatile uint32_t *)(FLASH_IF_BASE + 0x0C))
#define FLASH_CR        (*(volatile uint32_t *)(FLASH_IF_BASE + 0x10))

#define FLASH_KEY1      0x45670123
#define FLASH_KEY2      0xCDEF89AB

/* IWDG */
#define IWDG_BASE       0x40003000
#define IWDG_KR         (*(volatile uint32_t *)(IWDG_BASE + 0x00))
#define IWDG_PR         (*(volatile uint32_t *)(IWDG_BASE + 0x04))
#define IWDG_RLR        (*(volatile uint32_t *)(IWDG_BASE + 0x08))
#define IWDG_SR         (*(volatile uint32_t *)(IWDG_BASE + 0x0C))

/* USART2 */
#define USART2_BASE     0x40004400
#define USART2_SR       (*(volatile uint32_t *)(USART2_BASE + 0x00))
#define USART2_DR       (*(volatile uint32_t *)(USART2_BASE + 0x04))
#define USART2_BRR      (*(volatile uint32_t *)(USART2_BASE + 0x08))
#define USART2_CR1      (*(volatile uint32_t *)(USART2_BASE + 0x0C))

/* GPIO */
#define GPIOA_BASE      0x40020000
#define GPIOC_BASE      0x40020800
#define GPIO_MODER(b)   (*(volatile uint32_t *)((b) + 0x00))
#define GPIO_IDR(b)     (*(volatile uint32_t *)((b) + 0x10))
#define GPIO_AFRL(b)    (*(volatile uint32_t *)((b) + 0x20))

/* SCB */
#define SCB_VTOR        (*(volatile uint32_t *)0xE000ED08)
#define SCB_AIRCR       (*(volatile uint32_t *)0xE000ED0C)

/* SysTick */
#define SYSTICK_CTRL    (*(volatile uint32_t *)0xE000E010)
#define SYSTICK_LOAD    (*(volatile uint32_t *)0xE000E014)
#define SYSTICK_VAL     (*(volatile uint32_t *)0xE000E018)

/* NVIC */
#define NVIC_ICER_BASE  0xE000E180

static volatile uint32_t tick_ms = 0;

/* ---- Flash Operations ---- */

static int stm32f4_flash_read(uint32_t addr, void *buf, size_t len)
{
    memcpy(buf, (const void *)addr, len);
    return EOS_OK;
}

static void flash_unlock(void)
{
    if (FLASH_CR & (1 << 31)) { /* LOCK bit */
        FLASH_KEYR = FLASH_KEY1;
        FLASH_KEYR = FLASH_KEY2;
    }
}

static void flash_lock(void)
{
    FLASH_CR |= (1 << 31);
}

static void flash_wait_busy(void)
{
    while (FLASH_SR & (1 << 16)) /* BSY */
        ;
}

static int stm32f4_flash_write(uint32_t addr, const void *buf, size_t len)
{
    const uint8_t *src = (const uint8_t *)buf;

    flash_unlock();
    flash_wait_busy();

    /* Program byte-by-byte (PSIZE = 00 for x8) */
    FLASH_CR &= ~(3 << 8); /* Clear PSIZE */
    FLASH_CR |= (1 << 0);  /* PG bit */

    for (size_t i = 0; i < len; i++) {
        *(volatile uint8_t *)(addr + i) = src[i];
        flash_wait_busy();

        if (FLASH_SR & 0xF0) { /* Error flags */
            FLASH_SR = 0xF0; /* Clear errors */
            FLASH_CR &= ~(1 << 0);
            flash_lock();
            return EOS_ERR_FLASH;
        }
    }

    FLASH_CR &= ~(1 << 0); /* Clear PG */
    flash_lock();
    return EOS_OK;
}

static int stm32f4_flash_erase(uint32_t addr, size_t len)
{
    (void)len;

    /* Determine sector number from address */
    int sector = -1;
    if      (addr >= 0x08000000 && addr < 0x08004000) sector = 0;
    else if (addr >= 0x08004000 && addr < 0x08008000) sector = 1;
    else if (addr >= 0x08008000 && addr < 0x0800C000) sector = 2;
    else if (addr >= 0x0800C000 && addr < 0x08010000) sector = 3;
    else if (addr >= 0x08010000 && addr < 0x08020000) sector = 4;
    else if (addr >= 0x08020000 && addr < 0x08040000) sector = 5;
    else if (addr >= 0x08040000 && addr < 0x08060000) sector = 6;
    else if (addr >= 0x08060000 && addr < 0x08080000) sector = 7;
    else if (addr >= 0x08080000 && addr < 0x080A0000) sector = 8;
    else if (addr >= 0x080A0000 && addr < 0x080C0000) sector = 9;
    else if (addr >= 0x080C0000 && addr < 0x080E0000) sector = 10;
    else if (addr >= 0x080E0000 && addr < 0x08100000) sector = 11;

    if (sector < 0)
        return EOS_ERR_INVALID;

    flash_unlock();
    flash_wait_busy();

    FLASH_CR &= ~(0xF << 3);      /* Clear SNB bits */
    FLASH_CR |= (sector << 3);    /* Set sector number */
    FLASH_CR |= (1 << 1);         /* SER — sector erase */
    FLASH_CR |= (1 << 16);        /* STRT — start erase */

    flash_wait_busy();

    if (FLASH_SR & 0xF0) {
        FLASH_SR = 0xF0;
        FLASH_CR &= ~(1 << 1);
        flash_lock();
        return EOS_ERR_FLASH;
    }

    FLASH_CR &= ~(1 << 1); /* Clear SER */
    flash_lock();
    return EOS_OK;
}

/* ---- Watchdog ---- */

static void stm32f4_watchdog_init(uint32_t timeout_ms)
{
    /* LSI ≈ 32kHz. Prescaler /256 → ~125 Hz */
    IWDG_KR = 0x5555; /* Enable write access */
    IWDG_PR = 6;      /* Prescaler /256 */
    IWDG_RLR = (timeout_ms * 125) / 1000;
    if (IWDG_RLR > 0xFFF) IWDG_RLR = 0xFFF;
    IWDG_KR = 0xCCCC; /* Start IWDG */
}

static void stm32f4_watchdog_feed(void)
{
    IWDG_KR = 0xAAAA; /* Reload */
}

/* ---- Reset ---- */

static eos_reset_reason_t stm32f4_get_reset_reason(void)
{
    #define RCC_CSR (*(volatile uint32_t *)(RCC_BASE + 0x74))
    uint32_t csr = RCC_CSR;
    RCC_CSR |= (1 << 24); /* RMVF — clear flags */

    if (csr & (1 << 29)) return EOS_RESET_WATCHDOG;
    if (csr & (1 << 28)) return EOS_RESET_SOFTWARE;
    if (csr & (1 << 26)) return EOS_RESET_PIN;
    if (csr & (1 << 25)) return EOS_RESET_BROWNOUT;
    if (csr & (1 << 31)) return EOS_RESET_LOCKUP;

    return EOS_RESET_POWER_ON;
}

static void stm32f4_system_reset(void)
{
    SCB_AIRCR = (0x5FA << 16) | (1 << 2); /* SYSRESETREQ */
    while (1);
}

/* ---- Recovery Pin ---- */

static bool stm32f4_recovery_pin_asserted(void)
{
    /* PC13 — active low (pressed = 0) */
    RCC_AHB1ENR |= (1 << 2); /* Enable GPIOC clock */
    GPIO_MODER(GPIOC_BASE) &= ~(3 << (STM32F4_RECOVERY_PIN * 2)); /* Input mode */
    return !(GPIO_IDR(GPIOC_BASE) & (1 << STM32F4_RECOVERY_PIN));
}

/* ---- Jump ---- */

static void stm32f4_jump(uint32_t vector_addr)
{
#if defined(__ARM_ARCH) || defined(__arm__)
    uint32_t new_msp  = *(volatile uint32_t *)(vector_addr + 0);
    uint32_t reset_pc = *(volatile uint32_t *)(vector_addr + 4);

    SCB_VTOR = vector_addr;

    __asm volatile ("MSR MSP, %0" : : "r" (new_msp));
    __asm volatile ("BX %0" : : "r" (reset_pc));
#else
    (void)vector_addr;
#endif
}

/* ---- UART ---- */

static int stm32f4_uart_init(uint32_t baud)
{
    RCC_AHB1ENR |= (1 << 0);  /* Enable GPIOA clock */
    RCC_APB1ENR |= (1 << 17); /* Enable USART2 clock */

    /* PA2 = TX (AF7), PA3 = RX (AF7) */
    GPIO_MODER(GPIOA_BASE) &= ~((3 << 4) | (3 << 6));
    GPIO_MODER(GPIOA_BASE) |=  ((2 << 4) | (2 << 6)); /* Alternate function */
    GPIO_AFRL(GPIOA_BASE)  &= ~((0xF << 8) | (0xF << 12));
    GPIO_AFRL(GPIOA_BASE)  |=  ((7 << 8) | (7 << 12));   /* AF7 */

    /* Baud rate: assuming 16 MHz APB1 clock */
    USART2_BRR = 16000000 / baud;
    USART2_CR1 = (1 << 13) | (1 << 3) | (1 << 2); /* UE, TE, RE */

    return EOS_OK;
}

static int stm32f4_uart_send(const void *buf, size_t len)
{
    const uint8_t *p = (const uint8_t *)buf;
    for (size_t i = 0; i < len; i++) {
        while (!(USART2_SR & (1 << 7))); /* TXE */
        USART2_DR = p[i];
    }
    while (!(USART2_SR & (1 << 6))); /* TC */
    return EOS_OK;
}

static int stm32f4_uart_recv(void *buf, size_t len, uint32_t timeout_ms)
{
    uint8_t *p = (uint8_t *)buf;
    uint32_t start = tick_ms;

    for (size_t i = 0; i < len; i++) {
        while (!(USART2_SR & (1 << 5))) { /* RXNE */
            if ((tick_ms - start) >= timeout_ms)
                return EOS_ERR_TIMEOUT;
        }
        p[i] = (uint8_t)USART2_DR;
    }
    return EOS_OK;
}

/* ---- Timing ---- */

static uint32_t stm32f4_get_tick_ms(void)
{
    return tick_ms;
}

/* SysTick handler — increments every 1ms */
void SysTick_Handler(void)
{
    tick_ms++;
}

/* ---- Interrupt Control ---- */

static void stm32f4_disable_interrupts(void)
{
#if defined(__ARM_ARCH) || defined(__arm__)
    __asm volatile ("CPSID i");
#endif
}

static void stm32f4_enable_interrupts(void)
{
#if defined(__ARM_ARCH) || defined(__arm__)
    __asm volatile ("CPSIE i");
#endif
}

static void stm32f4_deinit_peripherals(void)
{
    /* Disable SysTick */
    SYSTICK_CTRL = 0;

    /* Disable all NVIC interrupts */
    for (int i = 0; i < 8; i++) {
        *(volatile uint32_t *)(NVIC_ICER_BASE + i * 4) = 0xFFFFFFFF;
    }

    /* Disable USART2 */
    USART2_CR1 = 0;
}

/* ---- Board Ops ---- */

static const eos_board_ops_t stm32f4_ops = {
    .flash_base          = STM32F4_FLASH_BASE,
    .flash_size          = STM32F4_FLASH_SIZE,
    .slot_a_addr         = STM32F4_SLOT_A_ADDR,
    .slot_a_size         = STM32F4_SLOT_A_SIZE,
    .slot_b_addr         = STM32F4_SLOT_B_ADDR,
    .slot_b_size         = STM32F4_SLOT_B_SIZE,
    .recovery_addr       = STM32F4_RECOVERY_ADDR,
    .recovery_size       = STM32F4_RECOVERY_SIZE,
    .bootctl_addr        = STM32F4_BOOTCTL_ADDR,
    .bootctl_backup_addr = STM32F4_BOOTCTL_BACKUP_ADDR,
    .log_addr            = STM32F4_LOG_ADDR,
    .app_vector_offset   = STM32F4_VECTOR_OFFSET,

    .flash_read          = stm32f4_flash_read,
    .flash_write         = stm32f4_flash_write,
    .flash_erase         = stm32f4_flash_erase,

    .watchdog_init       = stm32f4_watchdog_init,
    .watchdog_feed       = stm32f4_watchdog_feed,

    .get_reset_reason    = stm32f4_get_reset_reason,
    .system_reset        = stm32f4_system_reset,

    .recovery_pin_asserted = stm32f4_recovery_pin_asserted,

    .jump                = stm32f4_jump,

    .uart_init           = stm32f4_uart_init,
    .uart_send           = stm32f4_uart_send,
    .uart_recv           = stm32f4_uart_recv,

    .get_tick_ms         = stm32f4_get_tick_ms,

    .disable_interrupts  = stm32f4_disable_interrupts,
    .enable_interrupts   = stm32f4_enable_interrupts,
    .deinit_peripherals  = stm32f4_deinit_peripherals,
};

/* ---- Board Entry Points ---- */

void board_early_init(void)
{
    /* Enable HSI (16 MHz internal) — already running at reset */
    /* Set flash latency for 16 MHz */
    FLASH_ACR = (FLASH_ACR & ~0xF) | 0;

    /* Enable GPIOA, GPIOC clocks */
    RCC_AHB1ENR |= (1 << 0) | (1 << 2);

    /* Configure SysTick for 1ms interrupts (16 MHz / 1000) */
    SYSTICK_LOAD = 16000 - 1;
    SYSTICK_VAL  = 0;
    SYSTICK_CTRL = (1 << 0) | (1 << 1) | (1 << 2); /* Enable, interrupt, use processor clock */
}

const eos_board_ops_t *board_get_ops(void)
{
    return &stm32f4_ops;
}

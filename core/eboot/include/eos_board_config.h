// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_board_config.h
 * @brief Declarative hardware configuration — memory, pins, interrupts, clocks
 *
 * Provides a struct-based configuration model that separates WHAT
 * the hardware looks like from HOW it's accessed. Board porters
 * fill in a config struct instead of writing raw register code.
 *
 * Usage — define your board config in a header or C file:
 *
 *   static const eos_pin_config_t my_pins[] = {
 *       EOS_PIN_UART_TX(0, 'A', 2, 7),
 *       EOS_PIN_UART_RX(0, 'A', 3, 7),
 *       EOS_PIN_GPIO_OUT('C', 13),
 *       EOS_PIN_GPIO_IN_PU('C', 0),
 *   };
 *
 *   static const eos_mem_config_t my_mem[] = {
 *       EOS_MEM_FLASH(0x08000000, 1024 * 1024),
 *       EOS_MEM_RAM(0x20000000, 128 * 1024),
 *       EOS_MEM_PERIPH(0x40000000, 0x20000000),
 *   };
 *
 *   static const eos_irq_config_t my_irqs[] = {
 *       EOS_IRQ(USART2_IRQn, 3, true),
 *       EOS_IRQ(SysTick_IRQn, 0, true),
 *   };
 *
 *   static const eos_board_clock_config_t my_clocks = {
 *       .sysclk_hz = 168000000,
 *       .hclk_hz   = 168000000,
 *       .pclk1_hz  = 42000000,
 *       .pclk2_hz  = 84000000,
 *       .hse_hz    = 8000000,
 *       .use_pll   = true,
 *   };
 *
 *   static const eos_board_config_t my_board_config = {
 *       .name        = "my-custom-board",
 *       .pins        = my_pins,
 *       .pin_count   = sizeof(my_pins) / sizeof(my_pins[0]),
 *       .memory      = my_mem,
 *       .mem_count   = sizeof(my_mem) / sizeof(my_mem[0]),
 *       .irqs        = my_irqs,
 *       .irq_count   = sizeof(my_irqs) / sizeof(my_irqs[0]),
 *       .clocks      = &my_clocks,
 *   };
 *
 *   // Apply config during board init:
 *   eos_board_config_apply(&my_board_config);
 */

#ifndef EOS_BOARD_CONFIG_H
#define EOS_BOARD_CONFIG_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

/* ============================================================
 * Pin Configuration
 * ============================================================ */

typedef enum {
    EOS_PIN_MODE_INPUT       = 0,
    EOS_PIN_MODE_OUTPUT      = 1,
    EOS_PIN_MODE_AF          = 2,  /* Alternate function */
    EOS_PIN_MODE_ANALOG      = 3,
} eos_pin_mode_t;

typedef enum {
    EOS_PIN_PULL_NONE = 0,
    EOS_PIN_PULL_UP   = 1,
    EOS_PIN_PULL_DOWN = 2,
} eos_pin_pull_t;

typedef enum {
    EOS_PIN_SPEED_LOW    = 0,
    EOS_PIN_SPEED_MEDIUM = 1,
    EOS_PIN_SPEED_HIGH   = 2,
    EOS_PIN_SPEED_VHIGH  = 3,
} eos_pin_speed_t;

typedef enum {
    EOS_PIN_TYPE_PUSHPULL  = 0,
    EOS_PIN_TYPE_OPENDRAIN = 1,
} eos_pin_otype_t;

typedef enum {
    EOS_PIN_FUNC_GPIO    = 0,
    EOS_PIN_FUNC_UART_TX = 1,
    EOS_PIN_FUNC_UART_RX = 2,
    EOS_PIN_FUNC_SPI_SCK = 3,
    EOS_PIN_FUNC_SPI_MOSI = 4,
    EOS_PIN_FUNC_SPI_MISO = 5,
    EOS_PIN_FUNC_SPI_CS  = 6,
    EOS_PIN_FUNC_I2C_SCL = 7,
    EOS_PIN_FUNC_I2C_SDA = 8,
    EOS_PIN_FUNC_PWM     = 9,
    EOS_PIN_FUNC_ADC     = 10,
    EOS_PIN_FUNC_DAC     = 11,
    EOS_PIN_FUNC_CAN_TX  = 12,
    EOS_PIN_FUNC_CAN_RX  = 13,
    EOS_PIN_FUNC_USB_DP  = 14,
    EOS_PIN_FUNC_USB_DM  = 15,
    EOS_PIN_FUNC_ETH     = 16,
    EOS_PIN_FUNC_LED     = 17,
    EOS_PIN_FUNC_BUTTON  = 18,
    EOS_PIN_FUNC_RECOVERY = 19,
    EOS_PIN_FUNC_CUSTOM  = 0xFF,
} eos_pin_function_t;

typedef struct {
    char port;              /* Port letter: 'A', 'B', 'C', ... or 0 for port number */
    uint8_t port_num;       /* Port number (when port letter is 0) */
    uint8_t pin;            /* Pin number within port */
    eos_pin_mode_t mode;
    eos_pin_pull_t pull;
    eos_pin_speed_t speed;
    eos_pin_otype_t otype;
    uint8_t af_num;         /* Alternate function number (0-15) */
    eos_pin_function_t function;
    uint8_t periph_index;   /* Which UART/SPI/I2C instance this pin belongs to */
    bool initial_state;     /* Initial output state for GPIO outputs */
    bool active_low;        /* True if active-low (buttons, LEDs) */
} eos_pin_config_t;

/* Convenience macros for common pin configs */

#define EOS_PIN_UART_TX(uart_idx, port_letter, pin_num, af)  \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_AF,     \
      .pull = EOS_PIN_PULL_NONE, .speed = EOS_PIN_SPEED_HIGH,           \
      .otype = EOS_PIN_TYPE_PUSHPULL, .af_num = af,                     \
      .function = EOS_PIN_FUNC_UART_TX, .periph_index = uart_idx }

#define EOS_PIN_UART_RX(uart_idx, port_letter, pin_num, af)  \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_AF,     \
      .pull = EOS_PIN_PULL_UP, .speed = EOS_PIN_SPEED_HIGH,             \
      .otype = EOS_PIN_TYPE_PUSHPULL, .af_num = af,                     \
      .function = EOS_PIN_FUNC_UART_RX, .periph_index = uart_idx }

#define EOS_PIN_SPI_SCK(spi_idx, port_letter, pin_num, af)   \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_AF,     \
      .pull = EOS_PIN_PULL_NONE, .speed = EOS_PIN_SPEED_VHIGH,          \
      .af_num = af, .function = EOS_PIN_FUNC_SPI_SCK, .periph_index = spi_idx }

#define EOS_PIN_SPI_MOSI(spi_idx, port_letter, pin_num, af)  \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_AF,     \
      .pull = EOS_PIN_PULL_NONE, .speed = EOS_PIN_SPEED_VHIGH,          \
      .af_num = af, .function = EOS_PIN_FUNC_SPI_MOSI, .periph_index = spi_idx }

#define EOS_PIN_SPI_MISO(spi_idx, port_letter, pin_num, af)  \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_AF,     \
      .pull = EOS_PIN_PULL_NONE, .speed = EOS_PIN_SPEED_HIGH,           \
      .af_num = af, .function = EOS_PIN_FUNC_SPI_MISO, .periph_index = spi_idx }

#define EOS_PIN_I2C_SCL(i2c_idx, port_letter, pin_num, af)   \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_AF,     \
      .pull = EOS_PIN_PULL_UP, .speed = EOS_PIN_SPEED_HIGH,             \
      .otype = EOS_PIN_TYPE_OPENDRAIN, .af_num = af,                    \
      .function = EOS_PIN_FUNC_I2C_SCL, .periph_index = i2c_idx }

#define EOS_PIN_I2C_SDA(i2c_idx, port_letter, pin_num, af)   \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_AF,     \
      .pull = EOS_PIN_PULL_UP, .speed = EOS_PIN_SPEED_HIGH,             \
      .otype = EOS_PIN_TYPE_OPENDRAIN, .af_num = af,                    \
      .function = EOS_PIN_FUNC_I2C_SDA, .periph_index = i2c_idx }

#define EOS_PIN_GPIO_OUT(port_letter, pin_num)                \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_OUTPUT, \
      .pull = EOS_PIN_PULL_NONE, .speed = EOS_PIN_SPEED_LOW,            \
      .function = EOS_PIN_FUNC_GPIO }

#define EOS_PIN_GPIO_IN_PU(port_letter, pin_num)              \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_INPUT,  \
      .pull = EOS_PIN_PULL_UP, .function = EOS_PIN_FUNC_GPIO }

#define EOS_PIN_GPIO_IN_PD(port_letter, pin_num)              \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_INPUT,  \
      .pull = EOS_PIN_PULL_DOWN, .function = EOS_PIN_FUNC_GPIO }

#define EOS_PIN_LED(port_letter, pin_num, active_lo)          \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_OUTPUT, \
      .function = EOS_PIN_FUNC_LED, .active_low = active_lo }

#define EOS_PIN_BUTTON(port_letter, pin_num, active_lo)       \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_INPUT,  \
      .pull = EOS_PIN_PULL_UP, .function = EOS_PIN_FUNC_BUTTON,         \
      .active_low = active_lo }

#define EOS_PIN_RECOVERY_BTN(port_letter, pin_num)            \
    { .port = port_letter, .pin = pin_num, .mode = EOS_PIN_MODE_INPUT,  \
      .pull = EOS_PIN_PULL_UP, .function = EOS_PIN_FUNC_RECOVERY,       \
      .active_low = true }

/* ============================================================
 * Memory Region Configuration
 * ============================================================ */

typedef enum {
    EOS_MEM_TYPE_FLASH   = 0,
    EOS_MEM_TYPE_RAM     = 1,
    EOS_MEM_TYPE_PERIPH  = 2,
    EOS_MEM_TYPE_CCMRAM  = 3,  /* Core-coupled memory (STM32) */
    EOS_MEM_TYPE_DTCM    = 4,  /* Data TCM (Cortex-M7) */
    EOS_MEM_TYPE_ITCM    = 5,  /* Instruction TCM */
    EOS_MEM_TYPE_DMA     = 6,
    EOS_MEM_TYPE_SHARED  = 7,  /* Shared between cores (multicore) */
    EOS_MEM_TYPE_MMIO    = 8,  /* Memory-mapped I/O */
    EOS_MEM_TYPE_CUSTOM  = 0xFF,
} eos_mem_cfg_type_t;

typedef enum {
    EOS_MEM_PERM_RO   = 0,
    EOS_MEM_PERM_RW   = 1,
    EOS_MEM_PERM_RX   = 2,
    EOS_MEM_PERM_RWX  = 3,
    EOS_MEM_PERM_NONE = 4,
} eos_mem_perm_t;

typedef struct {
    const char *name;       /* Human-readable name ("Flash", "SRAM1", etc.) */
    uint32_t base;
    uint32_t size;
    eos_mem_cfg_type_t type;
    eos_mem_perm_t permission;
    bool cacheable;
    bool bufferable;
    bool shareable;         /* Shared between cores */
    uint8_t mpu_region;     /* MPU region number (0xFF = auto) */
} eos_mem_config_t;

/* Convenience macros */

#define EOS_MEM_FLASH(base_addr, sz)     \
    { .name = "Flash", .base = base_addr, .size = sz,       \
      .type = EOS_MEM_TYPE_FLASH, .permission = EOS_MEM_PERM_RX, \
      .cacheable = true, .mpu_region = 0xFF }

#define EOS_MEM_RAM(base_addr, sz)       \
    { .name = "RAM", .base = base_addr, .size = sz,         \
      .type = EOS_MEM_TYPE_RAM, .permission = EOS_MEM_PERM_RW,   \
      .cacheable = true, .bufferable = true, .mpu_region = 0xFF }

#define EOS_MEM_PERIPH(base_addr, sz)    \
    { .name = "Peripherals", .base = base_addr, .size = sz, \
      .type = EOS_MEM_TYPE_PERIPH, .permission = EOS_MEM_PERM_RW, \
      .shareable = true, .mpu_region = 0xFF }

#define EOS_MEM_SHARED(base_addr, sz)    \
    { .name = "Shared", .base = base_addr, .size = sz,      \
      .type = EOS_MEM_TYPE_SHARED, .permission = EOS_MEM_PERM_RW, \
      .shareable = true, .mpu_region = 0xFF }

#define EOS_MEM_CCMRAM(base_addr, sz)    \
    { .name = "CCMRAM", .base = base_addr, .size = sz,      \
      .type = EOS_MEM_TYPE_CCMRAM, .permission = EOS_MEM_PERM_RW, \
      .mpu_region = 0xFF }

#define EOS_MEM_DTCM(base_addr, sz)      \
    { .name = "DTCM", .base = base_addr, .size = sz,        \
      .type = EOS_MEM_TYPE_DTCM, .permission = EOS_MEM_PERM_RW,  \
      .mpu_region = 0xFF }

/* ============================================================
 * Interrupt Configuration
 * ============================================================ */

typedef struct {
    uint16_t irq_num;       /* Platform IRQ number */
    uint8_t  priority;      /* Priority (0 = highest) */
    uint8_t  subpriority;   /* Sub-priority */
    bool     enabled;       /* Enable on init */
    const char *name;       /* Human-readable name (optional) */
} eos_irq_config_t;

#define EOS_IRQ(num, prio, en)  \
    { .irq_num = num, .priority = prio, .enabled = en, .name = #num }

#define EOS_IRQ_NAMED(num, prio, en, label)  \
    { .irq_num = num, .priority = prio, .enabled = en, .name = label }

/* ============================================================
 * Clock Configuration
 * ============================================================ */

typedef enum {
    EOS_CLK_SRC_HSI  = 0,   /* High-speed internal */
    EOS_CLK_SRC_HSE  = 1,   /* High-speed external (crystal) */
    EOS_CLK_SRC_PLL  = 2,   /* PLL from HSI or HSE */
    EOS_CLK_SRC_LSI  = 3,   /* Low-speed internal (for watchdog/RTC) */
    EOS_CLK_SRC_LSE  = 4,   /* Low-speed external (32.768 kHz) */
} eos_clock_source_t;

typedef struct {
    /* System clock tree */
    eos_clock_source_t source;
    uint32_t sysclk_hz;     /* System clock frequency */
    uint32_t hclk_hz;       /* AHB bus clock */
    uint32_t pclk1_hz;      /* APB1 bus clock */
    uint32_t pclk2_hz;      /* APB2 bus clock */

    /* Input oscillators */
    uint32_t hsi_hz;        /* HSI frequency (usually fixed, e.g. 16 MHz) */
    uint32_t hse_hz;        /* HSE crystal frequency (0 = not used) */
    uint32_t lsi_hz;        /* LSI frequency (~32 kHz) */
    uint32_t lse_hz;        /* LSE crystal (32768 Hz, or 0) */

    /* PLL settings */
    bool     use_pll;
    uint16_t pll_m;         /* PLL input divider */
    uint16_t pll_n;         /* PLL multiplier */
    uint16_t pll_p;         /* PLL output divider (for SYSCLK) */
    uint16_t pll_q;         /* PLL output divider (for USB/SDIO) */

    /* Flash latency (wait states, auto-calculated if 0xFF) */
    uint8_t  flash_wait_states;

    /* Peripheral clocks enable mask */
    uint32_t ahb1_enable;   /* AHB1 peripheral clock enable bits */
    uint32_t ahb2_enable;   /* AHB2 peripheral clock enable bits */
    uint32_t apb1_enable;   /* APB1 peripheral clock enable bits */
    uint32_t apb2_enable;   /* APB2 peripheral clock enable bits */
} eos_board_clock_config_t;

/* ============================================================
 * Peripheral Enable Configuration
 * ============================================================ */

typedef enum {
    EOS_PERIPH_CFG_UART  = 0,
    EOS_PERIPH_CFG_SPI   = 1,
    EOS_PERIPH_CFG_I2C   = 2,
    EOS_PERIPH_CFG_TIMER = 3,
    EOS_PERIPH_CFG_ADC   = 4,
    EOS_PERIPH_CFG_DAC   = 5,
    EOS_PERIPH_CFG_USB   = 6,
    EOS_PERIPH_CFG_CAN   = 7,
    EOS_PERIPH_CFG_ETH   = 8,
    EOS_PERIPH_CFG_DMA   = 9,
    EOS_PERIPH_CFG_WDG   = 10,
} eos_periph_cfg_type_t;

typedef struct {
    eos_periph_cfg_type_t type;
    uint8_t index;          /* Peripheral instance (0 = UART0/USART1, etc.) */
    bool enabled;
    uint32_t base_addr;     /* Peripheral base address */
    uint16_t irq_num;       /* Primary IRQ */
    uint32_t clock_hz;      /* Peripheral clock frequency */

    /* UART-specific */
    uint32_t baudrate;

    /* SPI-specific */
    uint32_t spi_clock_hz;
    uint8_t  spi_mode;      /* 0-3 */

    /* I2C-specific */
    uint32_t i2c_clock_hz;  /* 100000 or 400000 */

    /* Timer-specific */
    uint32_t timer_period_us;
    bool     timer_auto_reload;
} eos_periph_config_t;

#define EOS_MAX_PERIPH_CONFIGS 16

/* ============================================================
 * Complete Board Configuration
 * ============================================================ */

#define EOS_MAX_MEM_CONFIGS  8
#define EOS_MAX_PIN_CONFIGS  32
#define EOS_MAX_IRQ_CONFIGS  32

typedef struct {
    const char *name;       /* Board name */
    const char *mcu;        /* MCU part number */
    uint32_t board_id;

    /* Pin configuration */
    const eos_pin_config_t *pins;
    uint8_t pin_count;

    /* Memory map */
    const eos_mem_config_t *memory;
    uint8_t mem_count;

    /* Interrupts */
    const eos_irq_config_t *irqs;
    uint8_t irq_count;

    /* Clocks */
    const eos_board_clock_config_t *clocks;

    /* Peripherals */
    const eos_periph_config_t *peripherals;
    uint8_t periph_count;
} eos_board_config_t;

/* ============================================================
 * Configuration API
 * ============================================================ */

/**
 * Apply a board configuration. Calls platform-specific init
 * for clocks, pins, memory regions, and interrupts.
 */
int eos_board_config_apply(const eos_board_config_t *cfg);

/**
 * Get the active board configuration.
 */
const eos_board_config_t *eos_board_config_get(void);

/**
 * Look up a pin by function (e.g. find the UART TX pin).
 */
const eos_pin_config_t *eos_board_config_find_pin(eos_pin_function_t func,
                                                    uint8_t periph_index);

/**
 * Look up a memory region by type.
 */
const eos_mem_config_t *eos_board_config_find_memory(eos_mem_cfg_type_t type);

/**
 * Look up a peripheral config by type and index.
 */
const eos_periph_config_t *eos_board_config_find_periph(eos_periph_cfg_type_t type,
                                                         uint8_t index);

/**
 * Get total RAM size from all configured RAM regions.
 */
uint32_t eos_board_config_total_ram(void);

/**
 * Get total flash size from all configured flash regions.
 */
uint32_t eos_board_config_total_flash(void);

/**
 * Print board config summary to UART (for debug/boot menu).
 */
void eos_board_config_dump(void);

/* ============================================================
 * Platform-specific config apply hooks (implemented by board port)
 * ============================================================ */

typedef struct {
    int (*apply_clocks)(const eos_board_clock_config_t *clk);
    int (*apply_pin)(const eos_pin_config_t *pin);
    int (*apply_memory)(const eos_mem_config_t *mem);
    int (*apply_irq)(const eos_irq_config_t *irq);
    int (*apply_periph)(const eos_periph_config_t *periph);
} eos_board_config_ops_t;

/**
 * Register platform-specific config apply handlers.
 */
void eos_board_config_set_ops(const eos_board_config_ops_t *ops);

#ifdef __cplusplus
}
#endif

#endif /* EOS_BOARD_CONFIG_H */

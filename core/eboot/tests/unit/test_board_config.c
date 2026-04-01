// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file test_board_config.c
 * @brief Unit tests for declarative board configuration
 */

#include "eos_board_config.h"
#include "eos_types.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int tests_run = 0;
static int tests_passed = 0;

#define TEST(name) \
    static void name(void); \
    static void run_##name(void) { \
        printf("  %-50s ", #name); \
        name(); \
        tests_passed++; \
        printf("[PASS]\n"); \
    } \
    static void name(void)

#define ASSERT(cond) do { \
    if (!(cond)) { \
        printf("[FAIL] %s:%d: %s\n", __FILE__, __LINE__, #cond); \
        exit(1); \
    } \
} while(0)

/* Sample config used across tests */

static const eos_pin_config_t test_pins[] = {
    EOS_PIN_UART_TX(0, 'A', 2, 7),
    EOS_PIN_UART_RX(0, 'A', 3, 7),
    EOS_PIN_GPIO_OUT('C', 13),
    EOS_PIN_LED('B', 0, false),
    EOS_PIN_RECOVERY_BTN('C', 0),
};

static const eos_mem_config_t test_mem[] = {
    EOS_MEM_FLASH(0x08000000, 1024 * 1024),
    EOS_MEM_RAM(0x20000000, 128 * 1024),
    EOS_MEM_CCMRAM(0x10000000, 64 * 1024),
};

static const eos_irq_config_t test_irqs[] = {
    EOS_IRQ(38, 3, true),
    EOS_IRQ(15, 0, true),
};

static const eos_board_clock_config_t test_clocks = {
    .source = EOS_CLK_SRC_PLL,
    .sysclk_hz = 168000000,
    .hclk_hz = 168000000,
    .pclk1_hz = 42000000,
    .pclk2_hz = 84000000,
    .hse_hz = 8000000,
    .use_pll = true,
    .pll_m = 8, .pll_n = 336, .pll_p = 2, .pll_q = 7,
};

static const eos_board_config_t test_config = {
    .name = "test-board",
    .mcu = "STM32F407VG",
    .board_id = 0x0413,
    .pins = test_pins,
    .pin_count = sizeof(test_pins) / sizeof(test_pins[0]),
    .memory = test_mem,
    .mem_count = sizeof(test_mem) / sizeof(test_mem[0]),
    .irqs = test_irqs,
    .irq_count = sizeof(test_irqs) / sizeof(test_irqs[0]),
    .clocks = &test_clocks,
};

TEST(test_apply_and_get)
{
    /* No platform ops registered — apply should still store config */
    eos_board_config_set_ops(NULL);
    int rc = eos_board_config_apply(&test_config);
    ASSERT(rc == EOS_OK);

    const eos_board_config_t *cfg = eos_board_config_get();
    ASSERT(cfg != NULL);
    ASSERT(strcmp(cfg->name, "test-board") == 0);
    ASSERT(strcmp(cfg->mcu, "STM32F407VG") == 0);
    ASSERT(cfg->pin_count == 5);
    ASSERT(cfg->mem_count == 3);
}

TEST(test_apply_null)
{
    ASSERT(eos_board_config_apply(NULL) == EOS_ERR_INVALID);
}

TEST(test_find_uart_tx_pin)
{
    eos_board_config_set_ops(NULL);
    eos_board_config_apply(&test_config);

    const eos_pin_config_t *pin = eos_board_config_find_pin(EOS_PIN_FUNC_UART_TX, 0);
    ASSERT(pin != NULL);
    ASSERT(pin->port == 'A');
    ASSERT(pin->pin == 2);
    ASSERT(pin->af_num == 7);
    ASSERT(pin->mode == EOS_PIN_MODE_AF);
}

TEST(test_find_uart_rx_pin)
{
    eos_board_config_set_ops(NULL);
    eos_board_config_apply(&test_config);

    const eos_pin_config_t *pin = eos_board_config_find_pin(EOS_PIN_FUNC_UART_RX, 0);
    ASSERT(pin != NULL);
    ASSERT(pin->port == 'A');
    ASSERT(pin->pin == 3);
    ASSERT(pin->pull == EOS_PIN_PULL_UP);
}

TEST(test_find_recovery_pin)
{
    eos_board_config_set_ops(NULL);
    eos_board_config_apply(&test_config);

    const eos_pin_config_t *pin = eos_board_config_find_pin(EOS_PIN_FUNC_RECOVERY, 0);
    ASSERT(pin != NULL);
    ASSERT(pin->port == 'C');
    ASSERT(pin->pin == 0);
    ASSERT(pin->active_low == true);
}

TEST(test_find_nonexistent_pin)
{
    eos_board_config_set_ops(NULL);
    eos_board_config_apply(&test_config);

    const eos_pin_config_t *pin = eos_board_config_find_pin(EOS_PIN_FUNC_CAN_TX, 0);
    ASSERT(pin == NULL);
}

TEST(test_find_flash_memory)
{
    eos_board_config_set_ops(NULL);
    eos_board_config_apply(&test_config);

    const eos_mem_config_t *mem = eos_board_config_find_memory(EOS_MEM_TYPE_FLASH);
    ASSERT(mem != NULL);
    ASSERT(mem->base == 0x08000000);
    ASSERT(mem->size == 1024 * 1024);
}

TEST(test_total_ram)
{
    eos_board_config_set_ops(NULL);
    eos_board_config_apply(&test_config);

    uint32_t total = eos_board_config_total_ram();
    /* RAM (128K) + CCMRAM (64K) = 192K */
    ASSERT(total == (128 + 64) * 1024);
}

TEST(test_total_flash)
{
    eos_board_config_set_ops(NULL);
    eos_board_config_apply(&test_config);

    uint32_t total = eos_board_config_total_flash();
    ASSERT(total == 1024 * 1024);
}

int main(void)
{
    printf("=== eBootloader: Board Config Unit Tests ===\n\n");

    run_test_apply_and_get();
    run_test_apply_null();
    run_test_find_uart_tx_pin();
    run_test_find_uart_rx_pin();
    run_test_find_recovery_pin();
    run_test_find_nonexistent_pin();
    run_test_find_flash_memory();
    run_test_total_ram();
    run_test_total_flash();

    tests_run = 9;
    printf("\n%d/%d tests passed\n", tests_passed, tests_run);
    return (tests_passed == tests_run) ? 0 : 1;
}

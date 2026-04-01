// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_dram.h
 * @brief DDR/DRAM initialization and training for SoCs with external memory
 *
 * Required for Cortex-A class SoCs (i.MX8M, AM64x, RPi4) that use
 * external DDR/LPDDR. MCUs with on-chip SRAM skip this.
 */

#ifndef EOS_DRAM_H
#define EOS_DRAM_H

#include "eos_types.h"

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    EOS_DRAM_DDR3,
    EOS_DRAM_DDR3L,
    EOS_DRAM_DDR4,
    EOS_DRAM_LPDDR4,
    EOS_DRAM_LPDDR4X,
    EOS_DRAM_LPDDR5,
    EOS_DRAM_DDR5
} eos_dram_type_t;

typedef struct {
    eos_dram_type_t type;
    uint32_t base_addr;
    uint32_t size_bytes;
    uint32_t bus_width;         /* 16, 32, 64 */
    uint32_t clock_mhz;
    uint32_t cas_latency;
    uint32_t ranks;
    uint32_t banks;
    bool     ecc_enabled;
    bool     training_done;
} eos_dram_config_t;

typedef struct {
    uint32_t read_delay;
    uint32_t write_delay;
    uint32_t dqs_delay;
    uint32_t clk_delay;
    bool     valid;
} eos_dram_training_t;

int  eos_dram_init(eos_dram_config_t *cfg);
int  eos_dram_train(eos_dram_config_t *cfg, eos_dram_training_t *result);
int  eos_dram_test(const eos_dram_config_t *cfg);
void eos_dram_dump(const eos_dram_config_t *cfg);

#ifdef __cplusplus
}
#endif
#endif /* EOS_DRAM_H */

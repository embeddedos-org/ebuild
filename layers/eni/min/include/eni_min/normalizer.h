// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef ENI_MIN_NORMALIZER_H
#define ENI_MIN_NORMALIZER_H

#include "eni/common.h"

typedef struct {
    eni_mode_t mode;
} eni_min_normalizer_t;

eni_status_t eni_min_normalizer_init(eni_min_normalizer_t *norm, eni_mode_t mode);
eni_status_t eni_min_normalizer_process(eni_min_normalizer_t *norm,
                                         const eni_event_t *raw,
                                         eni_event_t *normalized);

#endif /* ENI_MIN_NORMALIZER_H */

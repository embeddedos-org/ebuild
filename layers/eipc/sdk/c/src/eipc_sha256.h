// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

#ifndef EIPC_SHA256_INTERNAL_H
#define EIPC_SHA256_INTERNAL_H

#include <stdint.h>
#include <stddef.h>

void eipc_sha256(const uint8_t *data, size_t len, uint8_t out[32]);

#endif

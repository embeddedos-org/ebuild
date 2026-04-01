// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package core

import "errors"

var (
	ErrAuth         = errors.New("eipc: authentication failed")
	ErrCapability   = errors.New("eipc: capability check failed")
	ErrIntegrity    = errors.New("eipc: integrity verification failed")
	ErrReplay       = errors.New("eipc: replay detected")
	ErrTimeout      = errors.New("eipc: operation timed out")
	ErrBackpressure = errors.New("eipc: backpressure limit reached")
)

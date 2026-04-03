// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package protocol

// Header carries per-message routing and metadata, serialized as JSON in the frame.
type Header struct {
	ServiceID     string `json:"service_id"`
	SessionID     string `json:"session_id"`
	RequestID     string `json:"request_id"`
	Sequence      uint64 `json:"sequence"`
	Timestamp     string `json:"timestamp"`
	Priority      uint8  `json:"priority"`
	Capability    string `json:"capability,omitempty"`
	Route         string `json:"route,omitempty"`
	PayloadFormat uint8  `json:"payload_format"`
}

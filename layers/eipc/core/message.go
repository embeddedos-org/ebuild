// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package core

import "time"

// Message is the canonical EIPC message envelope exchanged between ENI and EAI.
type Message struct {
	Version    uint16      `json:"version"`
	Type       MessageType `json:"type"`
	Source     string      `json:"source"`
	Timestamp  time.Time   `json:"timestamp"`
	SessionID  string      `json:"session_id"`
	RequestID  string      `json:"request_id"`
	Priority   Priority    `json:"priority"`
	Capability string      `json:"capability"`
	Payload    []byte      `json:"payload"`
}

// NewMessage creates a message with defaults filled in.
func NewMessage(msgType MessageType, source string, payload []byte) Message {
	return Message{
		Version:   ProtocolVersion,
		Type:      msgType,
		Source:    source,
		Timestamp: time.Now().UTC(),
		Priority:  PriorityP1,
		Payload:   payload,
	}
}

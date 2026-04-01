// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package core

// MessageType identifies the kind of EIPC message.
type MessageType string

const (
	TypeIntent       MessageType = "intent"
	TypeFeatures     MessageType = "features"
	TypeToolRequest  MessageType = "tool_request"
	TypeAck          MessageType = "ack"
	TypePolicyResult MessageType = "policy_result"
	TypeHeartbeat    MessageType = "heartbeat"
	TypeAudit        MessageType = "audit"
)

// Priority defines message urgency lanes.
type Priority uint8

const (
	PriorityP0 Priority = 0 // Control-critical
	PriorityP1 Priority = 1 // Interactive
	PriorityP2 Priority = 2 // Telemetry
	PriorityP3 Priority = 3 // Debug / audit bulk
)

// PayloadFormat identifies serialization encoding.
type PayloadFormat uint8

const (
	PayloadJSON       PayloadFormat = 0
	PayloadMsgPack    PayloadFormat = 1
)

// ProtocolVersion is the current EIPC protocol version.
const ProtocolVersion uint16 = 1

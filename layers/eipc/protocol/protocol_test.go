// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package protocol_test

import (
	"bytes"
	"testing"
	"time"

	"github.com/embeddedos-org/eipc/core"
	"github.com/embeddedos-org/eipc/protocol"
)

func TestFrameRoundTrip(t *testing.T) {
	codec := protocol.DefaultCodec()

	hdr := protocol.Header{
		ServiceID:     "nia.min",
		SessionID:     "sess-1",
		RequestID:     "req-42",
		Sequence:      1,
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
		Priority:      uint8(core.PriorityP0),
		Capability:    "ui:control",
		PayloadFormat: uint8(core.PayloadJSON),
	}
	hdrBytes, err := codec.Marshal(hdr)
	if err != nil {
		t.Fatalf("marshal header: %v", err)
	}

	payload := core.IntentEvent{
		Intent:     "move_left",
		Confidence: 0.91,
		SessionID:  "sess-1",
	}
	payloadBytes, err := codec.Marshal(payload)
	if err != nil {
		t.Fatalf("marshal payload: %v", err)
	}

	original := &protocol.Frame{
		Version: protocol.ProtocolVersion,
		MsgType: uint8('i'),
		Flags:   0,
		Header:  hdrBytes,
		Payload: payloadBytes,
	}

	var buf bytes.Buffer
	if err := original.Encode(&buf); err != nil {
		t.Fatalf("encode: %v", err)
	}

	decoded, err := protocol.Decode(&buf)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}

	if decoded.Version != original.Version {
		t.Errorf("version: got %d, want %d", decoded.Version, original.Version)
	}
	if decoded.MsgType != original.MsgType {
		t.Errorf("msg_type: got %d, want %d", decoded.MsgType, original.MsgType)
	}
	if decoded.Flags != original.Flags {
		t.Errorf("flags: got %d, want %d", decoded.Flags, original.Flags)
	}
	if !bytes.Equal(decoded.Header, original.Header) {
		t.Errorf("header mismatch")
	}
	if !bytes.Equal(decoded.Payload, original.Payload) {
		t.Errorf("payload mismatch")
	}

	var decodedHdr protocol.Header
	if err := codec.Unmarshal(decoded.Header, &decodedHdr); err != nil {
		t.Fatalf("unmarshal header: %v", err)
	}
	if decodedHdr.ServiceID != hdr.ServiceID {
		t.Errorf("header service_id: got %q, want %q", decodedHdr.ServiceID, hdr.ServiceID)
	}
	if decodedHdr.Capability != hdr.Capability {
		t.Errorf("header capability: got %q, want %q", decodedHdr.Capability, hdr.Capability)
	}

	var decodedPayload core.IntentEvent
	if err := codec.Unmarshal(decoded.Payload, &decodedPayload); err != nil {
		t.Fatalf("unmarshal payload: %v", err)
	}
	if decodedPayload.Intent != payload.Intent {
		t.Errorf("payload intent: got %q, want %q", decodedPayload.Intent, payload.Intent)
	}
	if decodedPayload.Confidence != payload.Confidence {
		t.Errorf("payload confidence: got %f, want %f", decodedPayload.Confidence, payload.Confidence)
	}
}

func TestFrameWithHMAC(t *testing.T) {
	frame := &protocol.Frame{
		Version: protocol.ProtocolVersion,
		MsgType: uint8('a'),
		Flags:   protocol.FlagHMAC,
		Header:  []byte(`{"service_id":"test"}`),
		Payload: []byte(`{"status":"ok"}`),
		MAC:     make([]byte, protocol.MACSize),
	}
	for i := range frame.MAC {
		frame.MAC[i] = byte(i)
	}

	var buf bytes.Buffer
	if err := frame.Encode(&buf); err != nil {
		t.Fatalf("encode: %v", err)
	}

	decoded, err := protocol.Decode(&buf)
	if err != nil {
		t.Fatalf("decode: %v", err)
	}

	if !bytes.Equal(decoded.MAC, frame.MAC) {
		t.Errorf("MAC mismatch")
	}
}

func TestDecodeBadMagic(t *testing.T) {
	data := make([]byte, protocol.FrameFixedSize)
	data[0] = 0xFF
	_, err := protocol.Decode(bytes.NewReader(data))
	if err == nil {
		t.Error("expected error for bad magic")
	}
}

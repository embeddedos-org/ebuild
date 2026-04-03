// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package tcp

import (
	"testing"
	"time"

	"github.com/embeddedos-org/eipc/core"
	"github.com/embeddedos-org/eipc/protocol"
)

func TestTCPRoundTrip(t *testing.T) {
	srv := New()
	if err := srv.Listen("127.0.0.1:0"); err != nil {
		t.Fatalf("listen: %v", err)
	}
	defer srv.Close()

	addr := srv.Addr()

	codec := protocol.DefaultCodec()
	hdr := protocol.Header{
		ServiceID:     "test.client",
		SessionID:     "sess-test",
		RequestID:     "req-1",
		Sequence:      1,
		Timestamp:     time.Now().UTC().Format(time.RFC3339),
		Priority:      uint8(core.PriorityP1),
		PayloadFormat: uint8(core.PayloadJSON),
	}
	hdrBytes, _ := codec.Marshal(hdr)

	payload := core.IntentEvent{
		Intent:     "test_action",
		Confidence: 0.85,
		SessionID:  "sess-test",
	}
	payloadBytes, _ := codec.Marshal(payload)

	frame := &protocol.Frame{
		Version: core.ProtocolVersion,
		MsgType: uint8('i'),
		Flags:   0,
		Header:  hdrBytes,
		Payload: payloadBytes,
	}

	errCh := make(chan error, 1)
	frameCh := make(chan *protocol.Frame, 1)

	// Server goroutine
	go func() {
		conn, err := srv.Accept()
		if err != nil {
			errCh <- err
			return
		}
		defer conn.Close()

		received, err := conn.Receive()
		if err != nil {
			errCh <- err
			return
		}
		frameCh <- received
	}()

	// Client
	conn, err := srv.Dial(addr)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer conn.Close()

	if err := conn.Send(frame); err != nil {
		t.Fatalf("send: %v", err)
	}

	select {
	case err := <-errCh:
		t.Fatalf("server error: %v", err)
	case received := <-frameCh:
		if received.Version != frame.Version {
			t.Errorf("version: got %d, want %d", received.Version, frame.Version)
		}
		if received.MsgType != frame.MsgType {
			t.Errorf("msg_type: got %d, want %d", received.MsgType, frame.MsgType)
		}

		var decodedPayload core.IntentEvent
		if err := codec.Unmarshal(received.Payload, &decodedPayload); err != nil {
			t.Fatalf("unmarshal: %v", err)
		}
		if decodedPayload.Intent != payload.Intent {
			t.Errorf("intent: got %q, want %q", decodedPayload.Intent, payload.Intent)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("timeout waiting for frame")
	}
}

func TestTCPBidirectional(t *testing.T) {
	srv := New()
	if err := srv.Listen("127.0.0.1:0"); err != nil {
		t.Fatalf("listen: %v", err)
	}
	defer srv.Close()

	addr := srv.Addr()

	request := &protocol.Frame{
		Version: core.ProtocolVersion,
		MsgType: uint8('i'),
		Header:  []byte(`{"service_id":"client"}`),
		Payload: []byte(`{"intent":"ping"}`),
	}
	response := &protocol.Frame{
		Version: core.ProtocolVersion,
		MsgType: uint8('a'),
		Header:  []byte(`{"service_id":"server"}`),
		Payload: []byte(`{"status":"ok"}`),
	}

	errCh := make(chan error, 1)
	responseCh := make(chan *protocol.Frame, 1)

	go func() {
		srvConn, err := srv.Accept()
		if err != nil {
			errCh <- err
			return
		}
		defer srvConn.Close()

		if _, err := srvConn.Receive(); err != nil {
			errCh <- err
			return
		}
		if err := srvConn.Send(response); err != nil {
			errCh <- err
			return
		}
	}()

	clientConn, err := srv.Dial(addr)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer clientConn.Close()

	if err := clientConn.Send(request); err != nil {
		t.Fatalf("send: %v", err)
	}

	go func() {
		resp, err := clientConn.Receive()
		if err != nil {
			errCh <- err
			return
		}
		responseCh <- resp
	}()

	select {
	case err := <-errCh:
		t.Fatalf("error: %v", err)
	case resp := <-responseCh:
		if resp.MsgType != response.MsgType {
			t.Errorf("response type: got %d, want %d", resp.MsgType, response.MsgType)
		}
	case <-time.After(5 * time.Second):
		t.Fatal("timeout")
	}
}

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package core

import (
	"net"
	"testing"

	"github.com/embeddedos-org/eipc/protocol"
	"github.com/embeddedos-org/eipc/transport"
)

func setupTCPPair(t *testing.T) (transport.Connection, transport.Connection) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatalf("listen failed: %v", err)
	}
	defer ln.Close()

	acceptCh := make(chan net.Conn, 1)
	errCh := make(chan error, 1)
	go func() {
		conn, err := ln.Accept()
		if err != nil {
			errCh <- err
			return
		}
		acceptCh <- conn
	}()

	clientRaw, err := net.Dial("tcp", ln.Addr().String())
	if err != nil {
		t.Fatalf("dial failed: %v", err)
	}

	var serverRaw net.Conn
	select {
	case serverRaw = <-acceptCh:
	case err := <-errCh:
		t.Fatalf("accept failed: %v", err)
	}

	return transport.NewConnWrapper(clientRaw), transport.NewConnWrapper(serverRaw)
}

func TestClientEndpointSendReceive(t *testing.T) {
	clientConn, serverConn := setupTCPPair(t)
	defer clientConn.Close()
	defer serverConn.Close()

	hmacKey := []byte("test-secret-key-for-hmac-256bit!")
	sessionID := "test-session-001"
	c := protocol.DefaultCodec()

	clientEP := NewClientEndpoint(clientConn, c, hmacKey, sessionID)
	serverEP := NewServerEndpoint(serverConn, c, hmacKey)

	msg := NewMessage(TypeIntent, "test-service", []byte(`{"action":"ping"}`))
	msg.Priority = PriorityP0

	errCh := make(chan error, 1)
	msgCh := make(chan Message, 1)
	go func() {
		received, err := serverEP.Receive()
		if err != nil {
			errCh <- err
			return
		}
		msgCh <- received
	}()

	if err := clientEP.Send(msg); err != nil {
		t.Fatalf("Send failed: %v", err)
	}

	select {
	case received := <-msgCh:
		if received.Type != TypeIntent {
			t.Errorf("type mismatch: got %v, want %v", received.Type, TypeIntent)
		}
		if received.Source != "test-service" {
			t.Errorf("source mismatch: got %q, want %q", received.Source, "test-service")
		}
		if string(received.Payload) != `{"action":"ping"}` {
			t.Errorf("payload mismatch: got %q", string(received.Payload))
		}
	case err := <-errCh:
		t.Fatalf("Receive failed: %v", err)
	}
}

func TestHMACVerificationFailure(t *testing.T) {
	clientConn, serverConn := setupTCPPair(t)
	defer clientConn.Close()
	defer serverConn.Close()

	c := protocol.DefaultCodec()

	clientEP := NewClientEndpoint(clientConn, c, []byte("client-key-32-bytes-long-aaaaaa!"), "session-hmac")
	serverEP := NewServerEndpoint(serverConn, c, []byte("different-key-32-bytes-long-bbb!"))

	msg := NewMessage(TypeHeartbeat, "svc", []byte("beat"))

	errCh := make(chan error, 1)
	go func() {
		_, err := serverEP.Receive()
		errCh <- err
	}()

	if err := clientEP.Send(msg); err != nil {
		t.Fatalf("Send failed: %v", err)
	}

	err := <-errCh
	if err == nil {
		t.Fatal("expected HMAC verification error with mismatched keys")
	}
}

func TestHeartbeatMessage(t *testing.T) {
	msg := NewMessage(TypeHeartbeat, "monitor", nil)
	if msg.Type != TypeHeartbeat {
		t.Errorf("expected heartbeat type, got %v", msg.Type)
	}
	if msg.Source != "monitor" {
		t.Errorf("expected source 'monitor', got %q", msg.Source)
	}
}

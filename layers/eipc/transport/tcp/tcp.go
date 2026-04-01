// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package tcp

import (
	"fmt"
	"net"
	"sync"

	"github.com/embeddedos-org/eipc/transport"
)

// Transport implements the EIPC transport interface over TCP.
// Works on Linux, Windows, and macOS.
type Transport struct {
	mu       sync.Mutex
	listener net.Listener
}

// New creates a new TCP transport.
func New() *Transport {
	return &Transport{}
}

// Listen starts a TCP listener on the given address (e.g. "127.0.0.1:9090").
func (t *Transport) Listen(address string) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	ln, err := net.Listen("tcp", address)
	if err != nil {
		return fmt.Errorf("tcp listen: %w", err)
	}
	t.listener = ln
	return nil
}

// Dial connects to a remote TCP address and returns a Connection.
func (t *Transport) Dial(address string) (transport.Connection, error) {
	conn, err := net.Dial("tcp", address)
	if err != nil {
		return nil, fmt.Errorf("tcp dial: %w", err)
	}
	return transport.NewConnWrapper(conn), nil
}

// Accept waits for and returns the next inbound TCP connection.
func (t *Transport) Accept() (transport.Connection, error) {
	t.mu.Lock()
	ln := t.listener
	t.mu.Unlock()

	if ln == nil {
		return nil, fmt.Errorf("tcp: not listening")
	}

	conn, err := ln.Accept()
	if err != nil {
		return nil, fmt.Errorf("tcp accept: %w", err)
	}
	return transport.NewConnWrapper(conn), nil
}

// Close shuts down the TCP listener.
func (t *Transport) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.listener != nil {
		return t.listener.Close()
	}
	return nil
}

// Addr returns the listener's address. Returns "" if not listening.
func (t *Transport) Addr() string {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.listener != nil {
		return t.listener.Addr().String()
	}
	return ""
}

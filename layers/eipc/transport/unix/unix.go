// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

//go:build !windows

package unix

import (
	"fmt"
	"net"
	"sync"

	"github.com/embeddedos-org/eipc/transport"
)

// Transport implements the EIPC transport interface over Unix domain sockets.
type Transport struct {
	mu       sync.Mutex
	listener net.Listener
}

// New creates a new Unix domain socket transport.
func New() *Transport {
	return &Transport{}
}

// Listen starts a Unix domain socket listener on the given path.
func (t *Transport) Listen(address string) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	ln, err := net.Listen("unix", address)
	if err != nil {
		return fmt.Errorf("unix listen: %w", err)
	}
	t.listener = ln
	return nil
}

// Dial connects to a remote Unix domain socket and returns a Connection.
func (t *Transport) Dial(address string) (transport.Connection, error) {
	conn, err := net.Dial("unix", address)
	if err != nil {
		return nil, fmt.Errorf("unix dial: %w", err)
	}
	return transport.NewConnWrapper(conn), nil
}

// Accept waits for and returns the next inbound Unix connection.
func (t *Transport) Accept() (transport.Connection, error) {
	t.mu.Lock()
	ln := t.listener
	t.mu.Unlock()

	if ln == nil {
		return nil, fmt.Errorf("unix: not listening")
	}

	conn, err := ln.Accept()
	if err != nil {
		return nil, fmt.Errorf("unix accept: %w", err)
	}
	return transport.NewConnWrapper(conn), nil
}

// Close shuts down the Unix domain socket listener.
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

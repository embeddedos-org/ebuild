// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

//go:build windows

// Package windows provides a named-pipe-style transport for Windows.
// This implementation wraps TCP on localhost as a compatibility layer;
// a production version would use Windows named pipe syscalls
// (CreateNamedPipe / ConnectNamedPipe).
package windows

import (
	"fmt"
	"net"
	"sync"

	"github.com/embeddedos-org/eipc/transport"
)

type Transport struct {
	mu       sync.Mutex
	listener net.Listener
}

func New() *Transport {
	return &Transport{}
}

func (t *Transport) Listen(address string) error {
	t.mu.Lock()
	defer t.mu.Unlock()
	ln, err := net.Listen("tcp", address)
	if err != nil {
		return fmt.Errorf("windows pipe listen: %w", err)
	}
	t.listener = ln
	return nil
}

func (t *Transport) Dial(address string) (transport.Connection, error) {
	conn, err := net.Dial("tcp", address)
	if err != nil {
		return nil, fmt.Errorf("windows pipe dial: %w", err)
	}
	return transport.NewConnWrapper(conn), nil
}

func (t *Transport) Accept() (transport.Connection, error) {
	t.mu.Lock()
	ln := t.listener
	t.mu.Unlock()
	if ln == nil {
		return nil, fmt.Errorf("windows pipe: not listening")
	}
	conn, err := ln.Accept()
	if err != nil {
		return nil, fmt.Errorf("windows pipe accept: %w", err)
	}
	return transport.NewConnWrapper(conn), nil
}

func (t *Transport) Close() error {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.listener != nil {
		return t.listener.Close()
	}
	return nil
}

func (t *Transport) Addr() string {
	t.mu.Lock()
	defer t.mu.Unlock()
	if t.listener != nil {
		return t.listener.Addr().String()
	}
	return ""
}

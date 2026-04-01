// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

//go:build !windows

package unix

import (
	"os"
	"path/filepath"
	"testing"
)

func tempSocketPath(t *testing.T) string {
	t.Helper()
	dir := t.TempDir()
	return filepath.Join(dir, "test.sock")
}

func TestRoundTrip(t *testing.T) {
	sockPath := tempSocketPath(t)
	defer os.Remove(sockPath)

	serverTr := New()
	if err := serverTr.Listen(sockPath); err != nil {
		t.Fatalf("Listen failed: %v", err)
	}
	defer serverTr.Close()

	if addr := serverTr.Addr(); addr == "" {
		t.Fatal("Addr() returned empty after Listen")
	}

	errCh := make(chan error, 1)
	dataCh := make(chan string, 1)
	go func() {
		conn, err := serverTr.Accept()
		if err != nil {
			errCh <- err
			return
		}
		defer conn.Close()
		dataCh <- conn.RemoteAddr()
	}()

	clientTr := New()
	clientConn, err := clientTr.Dial(sockPath)
	if err != nil {
		t.Fatalf("Dial failed: %v", err)
	}
	defer clientConn.Close()

	select {
	case <-dataCh:
	case err := <-errCh:
		t.Fatalf("Accept failed: %v", err)
	}
}

func TestAcceptBeforeListen(t *testing.T) {
	tr := New()

	_, err := tr.Accept()
	if err == nil {
		t.Fatal("expected error when accepting without listening")
	}
}

func TestCloseWithoutListen(t *testing.T) {
	tr := New()
	if err := tr.Close(); err != nil {
		t.Fatalf("Close without listen should not error: %v", err)
	}
}

func TestAddrBeforeListen(t *testing.T) {
	tr := New()
	if addr := tr.Addr(); addr != "" {
		t.Errorf("Addr before listen should be empty, got %q", addr)
	}
}

func TestDialAndAccept(t *testing.T) {
	sockPath := tempSocketPath(t)
	defer os.Remove(sockPath)

	tr := New()
	if err := tr.Listen(sockPath); err != nil {
		t.Fatalf("Listen failed: %v", err)
	}
	defer tr.Close()

	doneCh := make(chan struct{}, 1)
	go func() {
		conn, err := tr.Accept()
		if err != nil {
			t.Errorf("Accept failed: %v", err)
			return
		}
		conn.Close()
		doneCh <- struct{}{}
	}()

	conn, err := tr.Dial(sockPath)
	if err != nil {
		t.Fatalf("Dial failed: %v", err)
	}
	conn.Close()
	<-doneCh
}

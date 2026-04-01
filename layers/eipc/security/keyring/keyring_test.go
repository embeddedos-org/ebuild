// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package keyring

import (
	"testing"
	"time"
)

func TestGenerateAndLookup(t *testing.T) {
	kr := New()
	entry, err := kr.Generate("hmac-key-1", 32, 0)
	if err != nil {
		t.Fatalf("Generate failed: %v", err)
	}
	if len(entry.Key) != 32 {
		t.Errorf("expected 32-byte key, got %d", len(entry.Key))
	}
	found, err := kr.Lookup("hmac-key-1")
	if err != nil {
		t.Fatalf("Lookup failed: %v", err)
	}
	if found.ID != entry.ID {
		t.Error("lookup returned wrong entry")
	}
}

func TestLookupNotFound(t *testing.T) {
	kr := New()
	_, err := kr.Lookup("nonexistent")
	if err == nil {
		t.Error("expected error for nonexistent key")
	}
}

func TestRevoke(t *testing.T) {
	kr := New()
	kr.Generate("key1", 16, 0)
	kr.Revoke("key1")
	_, err := kr.Lookup("key1")
	if err == nil {
		t.Error("expected error for revoked key")
	}
}

func TestExpiry(t *testing.T) {
	kr := New()
	kr.Generate("short", 16, 1*time.Millisecond)
	time.Sleep(5 * time.Millisecond)
	_, err := kr.Lookup("short")
	if err == nil {
		t.Error("expected error for expired key")
	}
}

func TestStore(t *testing.T) {
	kr := New()
	key := []byte("my-secret-key-32-bytes-00000000")
	kr.Store("ext", key, 0)
	found, err := kr.Lookup("ext")
	if err != nil {
		t.Fatalf("Lookup failed: %v", err)
	}
	if string(found.Key) != string(key) {
		t.Error("stored key mismatch")
	}
}

func TestRotate(t *testing.T) {
	kr := New()
	kr.Generate("rot", 32, 0)
	newEntry, err := kr.Rotate("rot", 32, 0)
	if err != nil {
		t.Fatalf("Rotate failed: %v", err)
	}
	found, _ := kr.Lookup("rot")
	if string(found.Key) != string(newEntry.Key) {
		t.Error("rotated key mismatch")
	}
}

func TestListActive(t *testing.T) {
	kr := New()
	kr.Generate("a1", 16, 0)
	kr.Generate("a2", 16, 0)
	kr.Generate("r1", 16, 0)
	kr.Revoke("r1")
	if len(kr.ListActive()) != 2 {
		t.Errorf("expected 2 active, got %d", len(kr.ListActive()))
	}
}

func TestCleanup(t *testing.T) {
	kr := New()
	kr.Generate("keep", 16, 0)
	kr.Generate("exp", 16, 1*time.Millisecond)
	kr.Generate("rev", 16, 0)
	kr.Revoke("rev")
	time.Sleep(5 * time.Millisecond)
	removed := kr.Cleanup()
	if removed != 2 {
		t.Errorf("expected 2 removed, got %d", removed)
	}
}

func TestDelete(t *testing.T) {
	kr := New()
	kr.Generate("del", 16, 0)
	kr.Delete("del")
	_, err := kr.Lookup("del")
	if err == nil {
		t.Error("expected error for deleted key")
	}
}

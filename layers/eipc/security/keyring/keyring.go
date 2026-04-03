// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package keyring

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync"
	"time"
)

type KeyEntry struct {
	ID        string
	Key       []byte
	CreatedAt time.Time
	ExpiresAt time.Time
	Revoked   bool
}

type Keyring struct {
	mu   sync.RWMutex
	keys map[string]*KeyEntry
}

func New() *Keyring {
	return &Keyring{keys: make(map[string]*KeyEntry)}
}

func (kr *Keyring) Generate(id string, keyLen int, ttl time.Duration) (*KeyEntry, error) {
	if id == "" {
		return nil, fmt.Errorf("key id is required")
	}
	if keyLen <= 0 {
		keyLen = 32
	}
	raw := make([]byte, keyLen)
	if _, err := rand.Read(raw); err != nil {
		return nil, fmt.Errorf("generate random key: %w", err)
	}
	now := time.Now().UTC()
	entry := &KeyEntry{ID: id, Key: raw, CreatedAt: now}
	if ttl > 0 {
		entry.ExpiresAt = now.Add(ttl)
	}
	kr.mu.Lock()
	defer kr.mu.Unlock()
	kr.keys[id] = entry
	return entry, nil
}

func (kr *Keyring) Store(id string, key []byte, ttl time.Duration) error {
	if id == "" || len(key) == 0 {
		return fmt.Errorf("id and key are required")
	}
	now := time.Now().UTC()
	entry := &KeyEntry{ID: id, Key: make([]byte, len(key)), CreatedAt: now}
	copy(entry.Key, key)
	if ttl > 0 {
		entry.ExpiresAt = now.Add(ttl)
	}
	kr.mu.Lock()
	defer kr.mu.Unlock()
	kr.keys[id] = entry
	return nil
}

func (kr *Keyring) Lookup(id string) (*KeyEntry, error) {
	kr.mu.RLock()
	defer kr.mu.RUnlock()
	entry, ok := kr.keys[id]
	if !ok {
		return nil, fmt.Errorf("key %q not found", id)
	}
	if entry.Revoked {
		return nil, fmt.Errorf("key %q has been revoked", id)
	}
	if !entry.ExpiresAt.IsZero() && time.Now().After(entry.ExpiresAt) {
		return nil, fmt.Errorf("key %q has expired", id)
	}
	return entry, nil
}

func (kr *Keyring) Revoke(id string) error {
	kr.mu.Lock()
	defer kr.mu.Unlock()
	entry, ok := kr.keys[id]
	if !ok {
		return fmt.Errorf("key %q not found", id)
	}
	entry.Revoked = true
	return nil
}

func (kr *Keyring) Delete(id string) {
	kr.mu.Lock()
	defer kr.mu.Unlock()
	delete(kr.keys, id)
}

func (kr *Keyring) Rotate(id string, keyLen int, ttl time.Duration) (*KeyEntry, error) {
	oldID := id + ".prev." + hex.EncodeToString(randomBytes(4))
	kr.mu.Lock()
	if old, ok := kr.keys[id]; ok {
		old.Revoked = true
		kr.keys[oldID] = old
		delete(kr.keys, id)
	}
	kr.mu.Unlock()
	return kr.Generate(id, keyLen, ttl)
}

func (kr *Keyring) ListActive() []KeyEntry {
	kr.mu.RLock()
	defer kr.mu.RUnlock()
	now := time.Now()
	var result []KeyEntry
	for _, e := range kr.keys {
		if e.Revoked {
			continue
		}
		if !e.ExpiresAt.IsZero() && now.After(e.ExpiresAt) {
			continue
		}
		result = append(result, *e)
	}
	return result
}

func (kr *Keyring) Cleanup() int {
	kr.mu.Lock()
	defer kr.mu.Unlock()
	now := time.Now()
	removed := 0
	for id, e := range kr.keys {
		if e.Revoked || (!e.ExpiresAt.IsZero() && now.After(e.ExpiresAt)) {
			delete(kr.keys, id)
			removed++
		}
	}
	return removed
}

func randomBytes(n int) []byte {
	b := make([]byte, n)
	rand.Read(b)
	return b
}

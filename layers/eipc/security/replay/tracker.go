// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package replay

import (
	"errors"
	"sync"
)

const defaultWindowSize = 128

// ErrReplay indicates a replayed or out-of-order message was detected.
var ErrReplay = errors.New("replay detected")

// Tracker detects replayed or out-of-order messages using a monotonic
// sequence number with a sliding window.
type Tracker struct {
	mu         sync.Mutex
	maxSeen    uint64
	windowSize uint64
	seen       map[uint64]struct{}
}

// NewTracker creates a replay tracker with the given sliding window size.
func NewTracker(windowSize int) *Tracker {
	ws := uint64(windowSize)
	if ws == 0 {
		ws = defaultWindowSize
	}
	return &Tracker{
		windowSize: ws,
		seen:       make(map[uint64]struct{}),
	}
}

// Check returns nil if the sequence number is valid (not replayed, not too old).
func (t *Tracker) Check(seq uint64) error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if seq == 0 {
		return ErrReplay
	}

	if seq > t.maxSeen {
		t.maxSeen = seq
		t.cleanup()
		t.seen[seq] = struct{}{}
		return nil
	}

	if t.maxSeen-seq > t.windowSize {
		return ErrReplay
	}

	if _, exists := t.seen[seq]; exists {
		return ErrReplay
	}

	t.seen[seq] = struct{}{}
	return nil
}

// Reset clears all tracked sequence numbers and resets the tracker state.
func (t *Tracker) Reset() {
	t.mu.Lock()
	defer t.mu.Unlock()
	t.maxSeen = 0
	t.seen = make(map[uint64]struct{})
}

func (t *Tracker) cleanup() {
	cutoff := uint64(0)
	if t.maxSeen > t.windowSize {
		cutoff = t.maxSeen - t.windowSize
	}
	for seq := range t.seen {
		if seq < cutoff {
			delete(t.seen, seq)
		}
	}
}

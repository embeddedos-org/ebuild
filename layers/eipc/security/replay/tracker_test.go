// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package replay

import (
	"testing"
)

func TestTrackerFirstCheck(t *testing.T) {
	tr := NewTracker(0) // default window size

	err := tr.Check(1)
	if err != nil {
		t.Fatalf("first check should pass: %v", err)
	}
}

func TestTrackerDuplicateRejection(t *testing.T) {
	tr := NewTracker(0)

	err := tr.Check(1)
	if err != nil {
		t.Fatalf("first check should pass: %v", err)
	}

	err = tr.Check(1)
	if err == nil {
		t.Fatal("expected ErrReplay for duplicate sequence")
	}
	if err != ErrReplay {
		t.Fatalf("expected ErrReplay, got: %v", err)
	}
}

func TestTrackerSlidingWindow(t *testing.T) {
	windowSize := 8
	tr := NewTracker(windowSize)

	// Fill window with sequential values
	for i := uint64(1); i <= uint64(windowSize); i++ {
		if err := tr.Check(i); err != nil {
			t.Fatalf("Check(%d) should pass: %v", i, err)
		}
	}

	// All values in window should be rejected as duplicates
	for i := uint64(1); i <= uint64(windowSize); i++ {
		if err := tr.Check(i); err == nil {
			t.Errorf("Check(%d) should fail as duplicate", i)
		}
	}

	// Next value after window should pass
	if err := tr.Check(uint64(windowSize) + 1); err != nil {
		t.Fatalf("Check(%d) should pass: %v", windowSize+1, err)
	}
}

func TestTrackerOutOfOrderWithinWindow(t *testing.T) {
	tr := NewTracker(16)

	// Process some out-of-order sequences
	if err := tr.Check(5); err != nil {
		t.Fatalf("Check(5) should pass: %v", err)
	}
	if err := tr.Check(3); err != nil {
		t.Fatalf("Check(3) should pass: %v", err)
	}
	if err := tr.Check(7); err != nil {
		t.Fatalf("Check(7) should pass: %v", err)
	}

	// Duplicates should still be rejected
	if err := tr.Check(5); err == nil {
		t.Fatal("Check(5) should fail as duplicate")
	}
	if err := tr.Check(3); err == nil {
		t.Fatal("Check(3) should fail as duplicate")
	}
}

func TestTrackerReset(t *testing.T) {
	tr := NewTracker(0)

	if err := tr.Check(1); err != nil {
		t.Fatalf("Check(1) should pass: %v", err)
	}
	if err := tr.Check(1); err == nil {
		t.Fatal("duplicate should be rejected before reset")
	}

	tr.Reset()

	if err := tr.Check(1); err != nil {
		t.Fatalf("Check(1) should pass after reset: %v", err)
	}
}

func TestTrackerDefaultWindowSize(t *testing.T) {
	tr := NewTracker(0) // should default to 128

	// Should be able to track at least 128 unique sequence numbers
	for i := uint64(1); i <= 128; i++ {
		if err := tr.Check(i); err != nil {
			t.Fatalf("Check(%d) should pass within default window: %v", i, err)
		}
	}
}

func TestTrackerGarbageCollection(t *testing.T) {
	windowSize := 4
	tr := NewTracker(windowSize)

	// Fill window and advance well beyond
	for i := uint64(1); i <= 20; i++ {
		if err := tr.Check(i); err != nil {
			t.Fatalf("Check(%d) should pass: %v", i, err)
		}
	}

	// Old sequence numbers far outside the window should either
	// be rejected (as too old) or cleaned up by GC
	err := tr.Check(1)
	if err == nil {
		t.Fatal("very old sequence number should be rejected")
	}
}

func TestTrackerSequentialUsage(t *testing.T) {
	tr := NewTracker(32)

	for i := uint64(1); i <= 100; i++ {
		if err := tr.Check(i); err != nil {
			t.Fatalf("sequential Check(%d) should pass: %v", i, err)
		}
	}
}

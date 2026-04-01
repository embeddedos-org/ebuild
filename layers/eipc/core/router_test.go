// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package core

import (
	"testing"
	"time"
)

func TestRouterHandle(t *testing.T) {
	r := NewRouter()

	called := false
	r.Handle(TypeIntent, func(msg Message) (*Message, error) {
		called = true
		resp := NewMessage(TypeAck, "router", []byte("handled"))
		return &resp, nil
	})

	msg := NewMessage(TypeIntent, "test", []byte("data"))
	resp, err := r.Dispatch(msg)
	if err != nil {
		t.Fatalf("Dispatch failed: %v", err)
	}
	if !called {
		t.Error("handler was not called")
	}
	if resp == nil {
		t.Fatal("expected response, got nil")
	}
	if resp.Type != TypeAck {
		t.Errorf("expected TypeAck, got %v", resp.Type)
	}
}

func TestRouterDispatchUnregistered(t *testing.T) {
	r := NewRouter()

	msg := NewMessage(TypeIntent, "test", nil)
	resp, err := r.Dispatch(msg)
	if err != nil {
		t.Fatalf("Dispatch should not error for unregistered type: %v", err)
	}
	if resp != nil {
		t.Error("expected nil response for unregistered type")
	}
}

func TestRouterBatchPriorityOrder(t *testing.T) {
	r := NewRouter()

	var order []Priority
	r.Handle(TypeIntent, func(msg Message) (*Message, error) {
		order = append(order, msg.Priority)
		return nil, nil
	})

	messages := []Message{
		{Type: TypeIntent, Priority: PriorityP2, Source: "low", Timestamp: time.Now()},
		{Type: TypeIntent, Priority: PriorityP0, Source: "critical", Timestamp: time.Now()},
		{Type: TypeIntent, Priority: PriorityP1, Source: "normal", Timestamp: time.Now()},
	}

	r.DispatchBatch(messages)

	if len(order) != 3 {
		t.Fatalf("expected 3 dispatches, got %d", len(order))
	}
	if order[0] != PriorityP0 {
		t.Errorf("first dispatch should be P0, got P%d", order[0])
	}
	if order[1] != PriorityP1 {
		t.Errorf("second dispatch should be P1, got P%d", order[1])
	}
	if order[2] != PriorityP2 {
		t.Errorf("third dispatch should be P2, got P%d", order[2])
	}
}

func TestRouterMultipleHandlers(t *testing.T) {
	r := NewRouter()

	intentCalled := false
	ackCalled := false

	r.Handle(TypeIntent, func(msg Message) (*Message, error) {
		intentCalled = true
		return nil, nil
	})
	r.Handle(TypeAck, func(msg Message) (*Message, error) {
		ackCalled = true
		return nil, nil
	})

	r.Dispatch(NewMessage(TypeIntent, "test", nil))
	r.Dispatch(NewMessage(TypeAck, "test", nil))

	if !intentCalled {
		t.Error("intent handler not called")
	}
	if !ackCalled {
		t.Error("ack handler not called")
	}
}

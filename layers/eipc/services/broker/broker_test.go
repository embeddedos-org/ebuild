// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package broker

import (
	"testing"

	"github.com/embeddedos-org/eipc/core"
)

type mockEndpoint struct {
	sent []core.Message
}

func (m *mockEndpoint) Send(msg core.Message) error {
	m.sent = append(m.sent, msg)
	return nil
}

func (m *mockEndpoint) Receive() (core.Message, error) {
	return core.Message{}, nil
}

func (m *mockEndpoint) Close() error {
	return nil
}

func TestBrokerSubscribeAndRoute(t *testing.T) {
	b := NewBroker(nil, nil)
	ep1 := &mockEndpoint{}
	ep2 := &mockEndpoint{}
	b.Subscribe(&Subscriber{ServiceID: "eai.agent", Endpoint: ep1, Priority: core.PriorityP1})
	b.Subscribe(&Subscriber{ServiceID: "eai.monitor", Endpoint: ep2, Priority: core.PriorityP2})
	b.AddRoute(core.TypeIntent, "eai.agent")
	msg := core.NewMessage(core.TypeIntent, "eni.min", []byte(`{"intent":"move_left"}`))
	results := b.Route(msg)
	if len(results) != 1 {
		t.Fatalf("expected 1 result, got %d", len(results))
	}
	if results[0].ServiceID != "eai.agent" {
		t.Errorf("expected eai.agent, got %s", results[0].ServiceID)
	}
	if len(ep1.sent) != 1 {
		t.Errorf("expected 1 msg to ep1, got %d", len(ep1.sent))
	}
}

func TestBrokerFanout(t *testing.T) {
	b := NewBroker(nil, nil)
	ep1 := &mockEndpoint{}
	ep2 := &mockEndpoint{}
	b.Subscribe(&Subscriber{ServiceID: "svc1", Endpoint: ep1})
	b.Subscribe(&Subscriber{ServiceID: "svc2", Endpoint: ep2})
	msg := core.NewMessage(core.TypeHeartbeat, "system", []byte(`{}`))
	results := b.Fanout(msg)
	if len(results) != 2 {
		t.Fatalf("expected 2 results, got %d", len(results))
	}
}

func TestBrokerUnsubscribe(t *testing.T) {
	b := NewBroker(nil, nil)
	ep := &mockEndpoint{}
	b.Subscribe(&Subscriber{ServiceID: "svc1", Endpoint: ep})
	if len(b.Subscribers()) != 1 {
		t.Fatal("expected 1 subscriber")
	}
	b.Unsubscribe("svc1")
	if len(b.Subscribers()) != 0 {
		t.Fatal("expected 0 subscribers")
	}
}

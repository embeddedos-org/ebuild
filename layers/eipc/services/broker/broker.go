// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package broker

import (
	"fmt"
	"sync"

	"github.com/embeddedos-org/eipc/core"
	"github.com/embeddedos-org/eipc/services/audit"
	"github.com/embeddedos-org/eipc/services/registry"
)

type Subscriber struct {
	ServiceID    string
	Capabilities []string
	Endpoint     core.Endpoint
	Priority     core.Priority
}

type Broker struct {
	mu          sync.RWMutex
	subscribers map[string]*Subscriber
	routes      map[core.MessageType][]string
	registry    *registry.Registry
	audit       audit.Logger
	router      *core.Router
	running     bool
}

func NewBroker(reg *registry.Registry, auditLogger audit.Logger) *Broker {
	return &Broker{
		subscribers: make(map[string]*Subscriber),
		routes:      make(map[core.MessageType][]string),
		registry:    reg,
		audit:       auditLogger,
		router:      core.NewRouter(),
	}
}

func (b *Broker) Subscribe(sub *Subscriber) error {
	if sub == nil || sub.ServiceID == "" || sub.Endpoint == nil {
		return fmt.Errorf("invalid subscriber: service_id and endpoint required")
	}
	b.mu.Lock()
	defer b.mu.Unlock()
	b.subscribers[sub.ServiceID] = sub
	return nil
}

func (b *Broker) Unsubscribe(serviceID string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	if sub, ok := b.subscribers[serviceID]; ok {
		sub.Endpoint.Close()
		delete(b.subscribers, serviceID)
	}
}

func (b *Broker) AddRoute(msgType core.MessageType, targets ...string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	existing := b.routes[msgType]
	seen := make(map[string]bool)
	for _, t := range existing {
		seen[t] = true
	}
	for _, t := range targets {
		if !seen[t] {
			existing = append(existing, t)
			seen[t] = true
		}
	}
	b.routes[msgType] = existing
}

func (b *Broker) RemoveRoute(msgType core.MessageType, target string) {
	b.mu.Lock()
	defer b.mu.Unlock()
	targets := b.routes[msgType]
	for i, t := range targets {
		if t == target {
			b.routes[msgType] = append(targets[:i], targets[i+1:]...)
			return
		}
	}
}

func (b *Broker) Route(msg core.Message) []RouteResult {
	b.mu.RLock()
	targets := b.routes[msg.Type]
	subs := make([]*Subscriber, 0, len(targets))
	for _, t := range targets {
		if sub, ok := b.subscribers[t]; ok {
			subs = append(subs, sub)
		}
	}
	b.mu.RUnlock()
	if len(subs) == 0 {
		return nil
	}
	sortByPriority(subs)
	results := make([]RouteResult, len(subs))
	for i, sub := range subs {
		err := sub.Endpoint.Send(msg)
		results[i] = RouteResult{ServiceID: sub.ServiceID, Err: err}
		if b.audit != nil {
			decision := "delivered"
			result := "ok"
			if err != nil {
				decision = "failed"
				result = err.Error()
			}
			b.audit.Log(audit.Entry{
				RequestID: msg.RequestID, Source: msg.Source,
				Target: sub.ServiceID, Action: string(msg.Type),
				Decision: decision, Result: result,
			})
		}
	}
	return results
}

func (b *Broker) Fanout(msg core.Message) []RouteResult {
	b.mu.RLock()
	subs := make([]*Subscriber, 0, len(b.subscribers))
	for _, sub := range b.subscribers {
		subs = append(subs, sub)
	}
	b.mu.RUnlock()
	results := make([]RouteResult, len(subs))
	for i, sub := range subs {
		err := sub.Endpoint.Send(msg)
		results[i] = RouteResult{ServiceID: sub.ServiceID, Err: err}
	}
	return results
}

func (b *Broker) Subscribers() []string {
	b.mu.RLock()
	defer b.mu.RUnlock()
	ids := make([]string, 0, len(b.subscribers))
	for id := range b.subscribers {
		ids = append(ids, id)
	}
	return ids
}

type RouteResult struct {
	ServiceID string
	Err       error
}

func sortByPriority(subs []*Subscriber) {
	for i := 1; i < len(subs); i++ {
		for j := i; j > 0 && subs[j].Priority < subs[j-1].Priority; j-- {
			subs[j], subs[j-1] = subs[j-1], subs[j]
		}
	}
}

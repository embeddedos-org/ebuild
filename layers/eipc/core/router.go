// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package core

import (
	"container/heap"
	"sync"
)

// HandlerFunc processes an incoming EIPC message and optionally returns a response.
type HandlerFunc func(msg Message) (*Message, error)

// Router dispatches incoming messages to registered handlers by message type.
// It supports priority-lane awareness: P0 messages are dispatched first.
type Router struct {
	mu       sync.RWMutex
	handlers map[MessageType]HandlerFunc
}

// NewRouter creates a new message router.
func NewRouter() *Router {
	return &Router{
		handlers: make(map[MessageType]HandlerFunc),
	}
}

// Handle registers a handler for the given message type.
func (r *Router) Handle(msgType MessageType, handler HandlerFunc) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.handlers[msgType] = handler
}

// Dispatch routes a single message to its registered handler.
func (r *Router) Dispatch(msg Message) (*Message, error) {
	r.mu.RLock()
	handler, ok := r.handlers[msg.Type]
	r.mu.RUnlock()

	if !ok {
		return nil, nil
	}
	return handler(msg)
}

// DispatchBatch processes a batch of messages in priority order (P0 first).
func (r *Router) DispatchBatch(messages []Message) []DispatchResult {
	pq := make(priorityQueue, len(messages))
	for i, msg := range messages {
		pq[i] = &priorityItem{msg: msg, index: i}
	}
	heap.Init(&pq)

	results := make([]DispatchResult, len(messages))
	for pq.Len() > 0 {
		item := heap.Pop(&pq).(*priorityItem)
		resp, err := r.Dispatch(item.msg)
		results[item.index] = DispatchResult{Response: resp, Err: err}
	}
	return results
}

// DispatchResult holds the outcome of dispatching a single message.
type DispatchResult struct {
	Response *Message
	Err      error
}

// Priority queue implementation for priority-lane dispatch.

type priorityItem struct {
	msg   Message
	index int
}

type priorityQueue []*priorityItem

func (pq priorityQueue) Len() int { return len(pq) }

func (pq priorityQueue) Less(i, j int) bool {
	return pq[i].msg.Priority < pq[j].msg.Priority // lower value = higher priority
}

func (pq priorityQueue) Swap(i, j int) {
	pq[i], pq[j] = pq[j], pq[i]
}

func (pq *priorityQueue) Push(x interface{}) {
	*pq = append(*pq, x.(*priorityItem))
}

func (pq *priorityQueue) Pop() interface{} {
	old := *pq
	n := len(old)
	item := old[n-1]
	old[n-1] = nil
	*pq = old[:n-1]
	return item
}

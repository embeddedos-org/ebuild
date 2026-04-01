// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package health

import (
	"sync"
	"time"
)

// PeerStatus tracks the liveness state of a peer.
type PeerStatus struct {
	ServiceID string
	Status    string
	LastSeen  time.Time
}

// Service sends and tracks heartbeat messages at configurable intervals.
type Service struct {
	mu       sync.RWMutex
	peers    map[string]*PeerStatus
	interval time.Duration
	timeout  time.Duration
}

// NewService creates a health service with the given heartbeat interval and
// liveness timeout.
func NewService(interval, timeout time.Duration) *Service {
	if interval == 0 {
		interval = 5 * time.Second
	}
	if timeout == 0 {
		timeout = 15 * time.Second
	}
	return &Service{
		peers:    make(map[string]*PeerStatus),
		interval: interval,
		timeout:  timeout,
	}
}

// RecordHeartbeat updates the liveness timestamp for a peer.
func (s *Service) RecordHeartbeat(serviceID, status string) {
	s.mu.Lock()
	defer s.mu.Unlock()

	s.peers[serviceID] = &PeerStatus{
		ServiceID: serviceID,
		Status:    status,
		LastSeen:  time.Now(),
	}
}

// IsAlive returns whether a peer has been heard from within the timeout window.
func (s *Service) IsAlive(serviceID string) bool {
	s.mu.RLock()
	defer s.mu.RUnlock()

	peer, ok := s.peers[serviceID]
	if !ok {
		return false
	}
	return time.Since(peer.LastSeen) <= s.timeout
}

// AllPeers returns a snapshot of all known peer statuses.
func (s *Service) AllPeers() []PeerStatus {
	s.mu.RLock()
	defer s.mu.RUnlock()

	result := make([]PeerStatus, 0, len(s.peers))
	for _, p := range s.peers {
		result = append(result, *p)
	}
	return result
}

// LivePeers returns only peers that are currently alive.
func (s *Service) LivePeers() []PeerStatus {
	s.mu.RLock()
	defer s.mu.RUnlock()

	now := time.Now()
	var result []PeerStatus
	for _, p := range s.peers {
		if now.Sub(p.LastSeen) <= s.timeout {
			result = append(result, *p)
		}
	}
	return result
}

// Interval returns the configured heartbeat interval.
func (s *Service) Interval() time.Duration {
	return s.interval
}

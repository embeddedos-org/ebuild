// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package auth

import (
	"crypto/rand"
	"encoding/hex"
	"fmt"
	"sync"

	"github.com/embeddedos-org/eipc/core"
)

// PeerIdentity represents an authenticated EIPC peer.
type PeerIdentity struct {
	ServiceID    string   `json:"service_id"`
	Capabilities []string `json:"capabilities"`
	SessionToken string   `json:"session_token"`
}

// Authenticator validates peer credentials and issues session tokens.
type Authenticator struct {
	mu             sync.RWMutex
	sharedSecret   []byte
	knownServices  map[string][]string // service_id → allowed capabilities
	activeSessions map[string]*PeerIdentity
}

// NewAuthenticator creates an authenticator with the given shared secret.
// knownServices maps service IDs to their allowed capability sets.
func NewAuthenticator(sharedSecret []byte, knownServices map[string][]string) *Authenticator {
	known := make(map[string][]string, len(knownServices))
	for k, v := range knownServices {
		caps := make([]string, len(v))
		copy(caps, v)
		known[k] = caps
	}
	return &Authenticator{
		sharedSecret:   sharedSecret,
		knownServices:  known,
		activeSessions: make(map[string]*PeerIdentity),
	}
}

// Authenticate validates a peer's service ID and returns a PeerIdentity
// with a fresh session token.
func (a *Authenticator) Authenticate(serviceID string) (*PeerIdentity, error) {
	a.mu.Lock()
	defer a.mu.Unlock()

	caps, ok := a.knownServices[serviceID]
	if !ok {
		return nil, fmt.Errorf("%w: unknown service %q", core.ErrAuth, serviceID)
	}

	token, err := generateToken()
	if err != nil {
		return nil, fmt.Errorf("generate token: %w", err)
	}

	peer := &PeerIdentity{
		ServiceID:    serviceID,
		Capabilities: caps,
		SessionToken: token,
	}
	a.activeSessions[token] = peer
	return peer, nil
}

// ValidateSession checks whether a session token is valid and returns the peer.
func (a *Authenticator) ValidateSession(token string) (*PeerIdentity, error) {
	a.mu.RLock()
	defer a.mu.RUnlock()

	peer, ok := a.activeSessions[token]
	if !ok {
		return nil, fmt.Errorf("%w: invalid session token", core.ErrAuth)
	}
	return peer, nil
}

// SharedSecret returns the shared HMAC key for message signing.
func (a *Authenticator) SharedSecret() []byte {
	return a.sharedSecret
}

// RevokeSession removes a session.
func (a *Authenticator) RevokeSession(token string) {
	a.mu.Lock()
	defer a.mu.Unlock()
	delete(a.activeSessions, token)
}

func generateToken() (string, error) {
	b := make([]byte, 32)
	if _, err := rand.Read(b); err != nil {
		return "", err
	}
	return hex.EncodeToString(b), nil
}

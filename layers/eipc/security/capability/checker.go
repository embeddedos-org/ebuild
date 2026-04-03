// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package capability

import (
	"fmt"
	"sync"

	"github.com/embeddedos-org/eipc/core"
)

// Checker enforces capability-based authorization.
// It maintains an allowlist of capabilities and the actions they permit.
type Checker struct {
	mu        sync.RWMutex
	allowlist map[string]map[string]struct{} // capability → set of allowed actions
}

// NewChecker creates a capability checker from an allowlist.
// The map keys are capability names, values are lists of permitted actions.
func NewChecker(allowlist map[string][]string) *Checker {
	al := make(map[string]map[string]struct{}, len(allowlist))
	for cap, actions := range allowlist {
		set := make(map[string]struct{}, len(actions))
		for _, a := range actions {
			set[a] = struct{}{}
		}
		al[cap] = set
	}
	return &Checker{allowlist: al}
}

// Check returns nil if any of peerCapabilities permits the given action.
func (c *Checker) Check(peerCapabilities []string, action string) error {
	c.mu.RLock()
	defer c.mu.RUnlock()

	for _, cap := range peerCapabilities {
		if actions, ok := c.allowlist[cap]; ok {
			if _, allowed := actions[action]; allowed {
				return nil
			}
		}
	}
	return fmt.Errorf("%w: no capability permits action %q", core.ErrCapability, action)
}

// Grant adds an action to a capability's allowlist at runtime.
func (c *Checker) Grant(capability, action string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if c.allowlist[capability] == nil {
		c.allowlist[capability] = make(map[string]struct{})
	}
	c.allowlist[capability][action] = struct{}{}
}

// Revoke removes an action from a capability's allowlist.
func (c *Checker) Revoke(capability, action string) {
	c.mu.Lock()
	defer c.mu.Unlock()

	if actions, ok := c.allowlist[capability]; ok {
		delete(actions, action)
	}
}

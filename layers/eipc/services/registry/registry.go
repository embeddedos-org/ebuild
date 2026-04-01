// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package registry

import (
	"fmt"
	"sync"

	"github.com/embeddedos-org/eipc/core"
)

// ServiceInfo describes a registered EIPC service.
type ServiceInfo struct {
	ServiceID    string             `json:"service_id"`
	Capabilities []string          `json:"capabilities"`
	Versions     []uint16          `json:"versions"`
	MessageTypes []core.MessageType `json:"message_types"`
	Priority     core.Priority      `json:"priority"`
}

// Registry is an in-memory service registry.
// Services register with declared capabilities, supported versions,
// message types, and priority classes.
type Registry struct {
	mu       sync.RWMutex
	services map[string]*ServiceInfo
}

// NewRegistry creates an empty service registry.
func NewRegistry() *Registry {
	return &Registry{
		services: make(map[string]*ServiceInfo),
	}
}

// Register adds or updates a service in the registry.
func (r *Registry) Register(info ServiceInfo) error {
	if info.ServiceID == "" {
		return fmt.Errorf("service_id is required")
	}

	r.mu.Lock()
	defer r.mu.Unlock()

	r.services[info.ServiceID] = &info
	return nil
}

// Deregister removes a service from the registry.
func (r *Registry) Deregister(serviceID string) {
	r.mu.Lock()
	defer r.mu.Unlock()
	delete(r.services, serviceID)
}

// Lookup returns a service's info, or an error if not found.
func (r *Registry) Lookup(serviceID string) (*ServiceInfo, error) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	info, ok := r.services[serviceID]
	if !ok {
		return nil, fmt.Errorf("service %q not found", serviceID)
	}
	return info, nil
}

// List returns all registered services.
func (r *Registry) List() []ServiceInfo {
	r.mu.RLock()
	defer r.mu.RUnlock()

	result := make([]ServiceInfo, 0, len(r.services))
	for _, info := range r.services {
		result = append(result, *info)
	}
	return result
}

// FindByCapability returns services that declare the given capability.
func (r *Registry) FindByCapability(cap string) []ServiceInfo {
	r.mu.RLock()
	defer r.mu.RUnlock()

	var result []ServiceInfo
	for _, info := range r.services {
		for _, c := range info.Capabilities {
			if c == cap {
				result = append(result, *info)
				break
			}
		}
	}
	return result
}

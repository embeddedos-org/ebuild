// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package capability

import (
	"testing"
)

func TestCheckerAllow(t *testing.T) {
	allowlist := map[string][]string{
		"cap:read":  {"read_sensor", "list_devices"},
		"cap:write": {"write_gpio", "set_config"},
	}

	c := NewChecker(allowlist)

	err := c.Check([]string{"cap:read"}, "read_sensor")
	if err != nil {
		t.Fatalf("expected allowed, got: %v", err)
	}
}

func TestCheckerDeny(t *testing.T) {
	allowlist := map[string][]string{
		"cap:read": {"read_sensor"},
	}

	c := NewChecker(allowlist)

	err := c.Check([]string{"cap:read"}, "write_gpio")
	if err == nil {
		t.Fatal("expected denial for unpermitted action")
	}
}

func TestCheckerMultipleCapabilities(t *testing.T) {
	allowlist := map[string][]string{
		"cap:read":  {"read_sensor"},
		"cap:write": {"write_gpio"},
	}

	c := NewChecker(allowlist)

	err := c.Check([]string{"cap:read", "cap:write"}, "write_gpio")
	if err != nil {
		t.Fatalf("should allow with multiple caps: %v", err)
	}
}

func TestCheckerGrant(t *testing.T) {
	c := NewChecker(map[string][]string{})

	err := c.Check([]string{"cap:admin"}, "restart_service")
	if err == nil {
		t.Fatal("expected denial before grant")
	}

	c.Grant("cap:admin", "restart_service")

	err = c.Check([]string{"cap:admin"}, "restart_service")
	if err != nil {
		t.Fatalf("expected allowed after grant: %v", err)
	}
}

func TestCheckerRevoke(t *testing.T) {
	allowlist := map[string][]string{
		"cap:write": {"write_gpio"},
	}

	c := NewChecker(allowlist)

	err := c.Check([]string{"cap:write"}, "write_gpio")
	if err != nil {
		t.Fatalf("should be allowed before revoke: %v", err)
	}

	c.Revoke("cap:write", "write_gpio")

	err = c.Check([]string{"cap:write"}, "write_gpio")
	if err == nil {
		t.Fatal("expected denial after revoke")
	}
}

func TestCheckerNoCapabilities(t *testing.T) {
	allowlist := map[string][]string{
		"cap:read": {"read_sensor"},
	}

	c := NewChecker(allowlist)

	err := c.Check([]string{}, "read_sensor")
	if err == nil {
		t.Fatal("expected denial with no capabilities")
	}
}

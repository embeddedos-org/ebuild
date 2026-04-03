// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package auth

import (
	"testing"
)

func TestAuthenticateKnownService(t *testing.T) {
	knownServices := map[string][]string{
		"service-a": {"cap:read", "cap:write"},
		"service-b": {"cap:read"},
	}

	a := NewAuthenticator([]byte("shared-secret"), knownServices)

	identity, err := a.Authenticate("service-a")
	if err != nil {
		t.Fatalf("Authenticate failed: %v", err)
	}
	if identity == nil {
		t.Fatal("expected identity, got nil")
	}
	if identity.ServiceID != "service-a" {
		t.Errorf("expected service-a, got %q", identity.ServiceID)
	}
	if len(identity.Capabilities) != 2 {
		t.Errorf("expected 2 capabilities, got %d", len(identity.Capabilities))
	}
}

func TestAuthenticateUnknownService(t *testing.T) {
	knownServices := map[string][]string{
		"service-a": {"cap:read"},
	}

	a := NewAuthenticator([]byte("shared-secret"), knownServices)

	_, err := a.Authenticate("unknown-service")
	if err == nil {
		t.Fatal("expected error for unknown service")
	}
}

func TestValidateSession(t *testing.T) {
	knownServices := map[string][]string{
		"service-a": {"cap:read", "cap:write"},
	}

	a := NewAuthenticator([]byte("shared-secret"), knownServices)

	identity, err := a.Authenticate("service-a")
	if err != nil {
		t.Fatalf("Authenticate failed: %v", err)
	}

	validated, err := a.ValidateSession(identity.SessionToken)
	if err != nil {
		t.Fatalf("ValidateSession failed: %v", err)
	}
	if validated == nil {
		t.Fatal("expected validated identity, got nil")
	}
	if validated.ServiceID != "service-a" {
		t.Errorf("expected service-a, got %q", validated.ServiceID)
	}
}

func TestValidateSessionInvalidToken(t *testing.T) {
	knownServices := map[string][]string{
		"service-a": {"cap:read"},
	}

	a := NewAuthenticator([]byte("shared-secret"), knownServices)

	_, err := a.ValidateSession("invalid-token-12345")
	if err == nil {
		t.Fatal("expected error for invalid token")
	}
}

func TestRevokeSession(t *testing.T) {
	knownServices := map[string][]string{
		"service-a": {"cap:read"},
	}

	a := NewAuthenticator([]byte("shared-secret"), knownServices)

	identity, err := a.Authenticate("service-a")
	if err != nil {
		t.Fatalf("Authenticate failed: %v", err)
	}

	a.RevokeSession(identity.SessionToken)

	_, err = a.ValidateSession(identity.SessionToken)
	if err == nil {
		t.Fatal("expected error after revoking session")
	}
}

func TestMultipleSessions(t *testing.T) {
	knownServices := map[string][]string{
		"service-a": {"cap:read"},
		"service-b": {"cap:write"},
	}

	a := NewAuthenticator([]byte("shared-secret"), knownServices)

	idA, err := a.Authenticate("service-a")
	if err != nil {
		t.Fatalf("Authenticate service-a failed: %v", err)
	}

	idB, err := a.Authenticate("service-b")
	if err != nil {
		t.Fatalf("Authenticate service-b failed: %v", err)
	}

	if idA.SessionToken == idB.SessionToken {
		t.Error("expected different tokens for different services")
	}

	a.RevokeSession(idA.SessionToken)

	_, err = a.ValidateSession(idA.SessionToken)
	if err == nil {
		t.Error("expected error for revoked token A")
	}

	_, err = a.ValidateSession(idB.SessionToken)
	if err != nil {
		t.Errorf("token B should still be valid: %v", err)
	}
}

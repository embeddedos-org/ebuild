// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package policy

import (
	"testing"
)

func TestPolicyAllowByRule(t *testing.T) {
	e := NewEngine(true, nil)
	e.AddRule(Rule{Action: "ui.cursor.move", Class: ActionSafe, Verdict: VerdictAllow})

	result := e.Evaluate(Request{Action: "ui.cursor.move", Source: "eni.min"})
	if !result.Allowed {
		t.Errorf("expected allowed, got denied: %s", result.Reason)
	}
}

func TestPolicyDenyByDefault(t *testing.T) {
	e := NewEngine(true, nil)

	result := e.Evaluate(Request{Action: "unknown.action", Source: "eni.min"})
	if result.Allowed {
		t.Error("expected denied (default deny), got allowed")
	}
}

func TestPolicyAllowByDefault(t *testing.T) {
	e := NewEngine(false, nil)

	result := e.Evaluate(Request{Action: "unknown.action", Source: "eni.min"})
	if !result.Allowed {
		t.Error("expected allowed (default allow), got denied")
	}
}

func TestPolicyDenyByRule(t *testing.T) {
	e := NewEngine(false, nil)
	e.AddRule(Rule{
		Action:      "system:shutdown",
		Class:       ActionRestricted,
		Verdict:     VerdictDeny,
		Description: "not allowed",
	})

	result := e.Evaluate(Request{Action: "system:shutdown", Source: "eni.min"})
	if result.Allowed {
		t.Error("expected denied by rule, got allowed")
	}
}

func TestPolicyConfirmVerdict(t *testing.T) {
	e := NewEngine(false, nil)
	e.AddRule(Rule{
		Action:  "firmware:update",
		Class:   ActionRestricted,
		Verdict: VerdictConfirm,
	})

	result := e.Evaluate(Request{Action: "firmware:update", Source: "eni.min"})
	if result.Allowed {
		t.Error("expected not allowed (confirm required)")
	}
	if result.Verdict != VerdictConfirm {
		t.Errorf("expected VerdictConfirm, got %d", result.Verdict)
	}
}

func TestPolicyCapabilityMismatch(t *testing.T) {
	e := NewEngine(false, nil)
	e.AddRule(Rule{
		Action:     "device:write",
		Class:      ActionControlled,
		Verdict:    VerdictAllow,
		Capability: "device:write",
	})

	result := e.Evaluate(Request{
		Action:     "device:write",
		Capability: "ui:control",
		Source:     "eni.min",
	})
	if result.Allowed {
		t.Error("expected denied (capability mismatch), got allowed")
	}
}

func TestPolicyCapabilityMatch(t *testing.T) {
	e := NewEngine(false, nil)
	e.AddRule(Rule{
		Action:     "device:write",
		Class:      ActionControlled,
		Verdict:    VerdictAllow,
		Capability: "device:write",
	})

	result := e.Evaluate(Request{
		Action:     "device:write",
		Capability: "device:write",
		Source:     "eni.min",
	})
	if !result.Allowed {
		t.Errorf("expected allowed, got denied: %s", result.Reason)
	}
}

func TestPolicySafeDefaults(t *testing.T) {
	e := NewEngine(true, nil)
	e.LoadSafeDefaults()

	safe := e.Evaluate(Request{Action: "ui.cursor.move", Source: "eni"})
	if !safe.Allowed {
		t.Error("safe action should be allowed")
	}

	restricted := e.Evaluate(Request{Action: "system:reboot", Source: "eni"})
	if restricted.Allowed {
		t.Error("restricted action should not be allowed without confirmation")
	}
	if restricted.Verdict != VerdictConfirm {
		t.Errorf("expected VerdictConfirm for restricted action, got %d", restricted.Verdict)
	}
}

func TestPolicyRemoveRule(t *testing.T) {
	e := NewEngine(true, nil)
	e.AddRule(Rule{Action: "test.action", Verdict: VerdictAllow})

	r1 := e.Evaluate(Request{Action: "test.action"})
	if !r1.Allowed {
		t.Error("expected allowed before removal")
	}

	e.RemoveRule("test.action")

	r2 := e.Evaluate(Request{Action: "test.action"})
	if r2.Allowed {
		t.Error("expected denied after removal (default deny)")
	}
}

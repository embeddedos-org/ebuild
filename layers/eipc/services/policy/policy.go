// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package policy

import (
	"fmt"
	"sync"
	"time"

	"github.com/embeddedos-org/eipc/core"
	"github.com/embeddedos-org/eipc/services/audit"
)

// ActionClass categorizes actions by risk level.
type ActionClass int

const (
	ActionSafe       ActionClass = iota // UI control, read-only
	ActionControlled                    // Device writes
	ActionRestricted                    // System operations
)

// Verdict is the policy decision for an action.
type Verdict int

const (
	VerdictAllow   Verdict = iota
	VerdictDeny
	VerdictConfirm // Requires operator approval
)

// Rule defines a single policy rule.
type Rule struct {
	Action      string
	Class       ActionClass
	Verdict     Verdict
	Capability  string
	Description string
}

// Request represents an action request to be evaluated.
type Request struct {
	Source      string
	Action     string
	Capability string
	RequestID  string
}

// Result is the outcome of a policy evaluation.
type Result struct {
	Allowed   bool
	Verdict   Verdict
	Reason    string
	RequestID string
	Timestamp time.Time
}

// Engine evaluates policy rules for incoming EIPC requests.
// It implements the EIPC security model: identity check → capability check →
// policy check → tool execution → audit log.
type Engine struct {
	mu          sync.RWMutex
	rules       map[string]*Rule
	defaultDeny bool
	audit       audit.Logger
}

// NewEngine creates a policy engine. If defaultDeny is true,
// any action without an explicit rule is denied.
func NewEngine(defaultDeny bool, auditLogger audit.Logger) *Engine {
	return &Engine{
		rules:       make(map[string]*Rule),
		defaultDeny: defaultDeny,
		audit:       auditLogger,
	}
}

// AddRule registers a policy rule for the given action.
func (e *Engine) AddRule(rule Rule) error {
	if rule.Action == "" {
		return fmt.Errorf("rule action is required")
	}

	e.mu.Lock()
	defer e.mu.Unlock()

	e.rules[rule.Action] = &rule
	return nil
}

// RemoveRule removes a policy rule.
func (e *Engine) RemoveRule(action string) {
	e.mu.Lock()
	defer e.mu.Unlock()
	delete(e.rules, action)
}

// Evaluate checks whether a request is allowed by policy.
func (e *Engine) Evaluate(req Request) Result {
	e.mu.RLock()
	rule, exists := e.rules[req.Action]
	defaultDeny := e.defaultDeny
	e.mu.RUnlock()

	result := Result{
		RequestID: req.RequestID,
		Timestamp: time.Now().UTC(),
	}

	if !exists {
		if defaultDeny {
			result.Allowed = false
			result.Verdict = VerdictDeny
			result.Reason = fmt.Sprintf("no rule for action %q, default deny", req.Action)
		} else {
			result.Allowed = true
			result.Verdict = VerdictAllow
			result.Reason = "no rule, default allow"
		}
	} else {
		switch rule.Verdict {
		case VerdictAllow:
			if rule.Capability != "" && rule.Capability != req.Capability {
				result.Allowed = false
				result.Verdict = VerdictDeny
				result.Reason = fmt.Sprintf("capability mismatch: need %q, have %q",
					rule.Capability, req.Capability)
			} else {
				result.Allowed = true
				result.Verdict = VerdictAllow
				result.Reason = "allowed by rule"
			}
		case VerdictDeny:
			result.Allowed = false
			result.Verdict = VerdictDeny
			result.Reason = fmt.Sprintf("denied by rule: %s", rule.Description)
		case VerdictConfirm:
			result.Allowed = false
			result.Verdict = VerdictConfirm
			result.Reason = "requires operator confirmation"
		}
	}

	if e.audit != nil {
		decision := "allow"
		if !result.Allowed {
			decision = "deny"
		}
		e.audit.Log(audit.Entry{
			RequestID: req.RequestID,
			Source:    req.Source,
			Action:   req.Action,
			Decision: decision,
			Result:   result.Reason,
		})
	}

	return result
}

// EvaluateMessage is a convenience method that evaluates a core.Message.
func (e *Engine) EvaluateMessage(msg core.Message) Result {
	return e.Evaluate(Request{
		Source:     msg.Source,
		Action:     string(msg.Type),
		Capability: msg.Capability,
		RequestID:  msg.RequestID,
	})
}

// ListRules returns all registered rules.
func (e *Engine) ListRules() []Rule {
	e.mu.RLock()
	defer e.mu.RUnlock()

	rules := make([]Rule, 0, len(e.rules))
	for _, r := range e.rules {
		rules = append(rules, *r)
	}
	return rules
}

// SetDefaultDeny changes the default deny policy.
func (e *Engine) SetDefaultDeny(deny bool) {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.defaultDeny = deny
}

// LoadSafeDefaults adds permissive rules for safe action classes
// and restrictive rules for controlled/restricted classes.
func (e *Engine) LoadSafeDefaults() {
	safeActions := []string{
		"ui.cursor.move", "ui.scroll", "ui.select", "ui.focus",
		"sensor:read", "device:read", "status:read",
	}
	for _, a := range safeActions {
		e.AddRule(Rule{
			Action:  a,
			Class:   ActionSafe,
			Verdict: VerdictAllow,
		})
	}

	controlledActions := []string{
		"device:write", "actuator:write", "motor:move",
		"iot:publish", "config:write",
	}
	for _, a := range controlledActions {
		e.AddRule(Rule{
			Action:     a,
			Class:      ActionControlled,
			Verdict:    VerdictAllow,
			Capability: "device:write",
		})
	}

	restrictedActions := []string{
		"system:reboot", "system:shutdown", "firmware:update",
		"security:modify", "policy:modify",
	}
	for _, a := range restrictedActions {
		e.AddRule(Rule{
			Action:      a,
			Class:       ActionRestricted,
			Verdict:     VerdictConfirm,
			Description: "restricted system operation",
		})
	}
}

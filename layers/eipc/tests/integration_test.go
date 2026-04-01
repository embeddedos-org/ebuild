// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package integration_test

import (
	"encoding/json"
	"fmt"
	"sync"
	"testing"
	"time"

	"github.com/embeddedos-org/eipc/core"
	"github.com/embeddedos-org/eipc/protocol"
	"github.com/embeddedos-org/eipc/security/auth"
	"github.com/embeddedos-org/eipc/security/capability"
	"github.com/embeddedos-org/eipc/security/integrity"
	"github.com/embeddedos-org/eipc/security/keyring"
	"github.com/embeddedos-org/eipc/services/audit"
	"github.com/embeddedos-org/eipc/services/broker"
	"github.com/embeddedos-org/eipc/services/health"
	"github.com/embeddedos-org/eipc/services/policy"
	"github.com/embeddedos-org/eipc/services/registry"
)

type memEndpoint struct {
	mu     sync.Mutex
	inbox  []core.Message
	outbox chan core.Message
	closed bool
}

func newMemEndpoint() *memEndpoint {
	return &memEndpoint{outbox: make(chan core.Message, 64)}
}
func (e *memEndpoint) Send(msg core.Message) error {
	e.mu.Lock()
	defer e.mu.Unlock()
	e.inbox = append(e.inbox, msg)
	select {
	case e.outbox <- msg:
	default:
	}
	return nil
}
func (e *memEndpoint) Receive() (core.Message, error) {
	msg, ok := <-e.outbox
	if !ok {
		return core.Message{}, fmt.Errorf("closed")
	}
	return msg, nil
}
func (e *memEndpoint) Close() error { return nil }
func (e *memEndpoint) received() []core.Message {
	e.mu.Lock()
	defer e.mu.Unlock()
	cp := make([]core.Message, len(e.inbox))
	copy(cp, e.inbox)
	return cp
}

type memAuditLogger struct {
	mu      sync.Mutex
	entries []audit.Entry
}

func (l *memAuditLogger) Log(entry audit.Entry) error {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.entries = append(l.entries, entry)
	return nil
}
func (l *memAuditLogger) Close() error { return nil }
func (l *memAuditLogger) Entries() []audit.Entry {
	l.mu.Lock()
	defer l.mu.Unlock()
	cp := make([]audit.Entry, len(l.entries))
	copy(cp, l.entries)
	return cp
}

func TestENI_EIPC_EAI_IntentFlow(t *testing.T) {
	hmacKey := []byte("test-hmac-secret-key-32bytes!!")
	auditLog := &memAuditLogger{}
	codec := protocol.DefaultCodec()

	reg := registry.NewRegistry()
	reg.Register(registry.ServiceInfo{ServiceID: "eni.min", Capabilities: []string{"ui:control"}, Versions: []uint16{1}, MessageTypes: []core.MessageType{core.TypeIntent}, Priority: core.PriorityP1})
	reg.Register(registry.ServiceInfo{ServiceID: "eai.min.agent", Capabilities: []string{"tool:execute"}, Versions: []uint16{1}, MessageTypes: []core.MessageType{core.TypeIntent, core.TypeAck}, Priority: core.PriorityP1})

	authenticator := auth.NewAuthenticator(hmacKey, map[string][]string{"eni.min": {"ui:control"}, "eai.min.agent": {"tool:execute"}})
	eniPeer, _ := authenticator.Authenticate("eni.min")
	authenticator.Authenticate("eai.min.agent")

	capChecker := capability.NewChecker(map[string][]string{"ui:control": {"ui.cursor.move"}})
	policyEngine := policy.NewEngine(true, auditLog)
	policyEngine.LoadSafeDefaults()

	brk := broker.NewBroker(reg, auditLog)
	eaiEP := newMemEndpoint()
	brk.Subscribe(&broker.Subscriber{ServiceID: "eai.min.agent", Endpoint: eaiEP, Priority: core.PriorityP1})
	brk.AddRoute(core.TypeIntent, "eai.min.agent")

	intentEvent := core.IntentEvent{Intent: "move_left", Confidence: 0.91, SessionID: "sess-001"}
	payload, _ := codec.Marshal(intentEvent)
	intentMsg := core.Message{Version: core.ProtocolVersion, Type: core.TypeIntent, Source: "eni.min", Timestamp: time.Now().UTC(), SessionID: "sess-001", RequestID: "req-001", Priority: core.PriorityP1, Capability: "ui:control", Payload: payload}

	validatedPeer, _ := authenticator.ValidateSession(eniPeer.SessionToken)
	if validatedPeer.ServiceID != "eni.min" {
		t.Fatalf("expected eni.min, got %s", validatedPeer.ServiceID)
	}
	if err := capChecker.Check(validatedPeer.Capabilities, "ui.cursor.move"); err != nil {
		t.Fatalf("capability check failed: %v", err)
	}
	pr := policyEngine.Evaluate(policy.Request{Source: "eni.min", Action: "ui.cursor.move", Capability: "ui:control", RequestID: "req-001"})
	if !pr.Allowed {
		t.Fatalf("policy denied: %s", pr.Reason)
	}
	results := brk.Route(intentMsg)
	if len(results) == 0 || results[0].Err != nil {
		t.Fatal("route failed")
	}
	msgs := eaiEP.received()
	if len(msgs) != 1 || msgs[0].Type != core.TypeIntent {
		t.Fatalf("expected 1 intent, got %d", len(msgs))
	}
	var decoded core.IntentEvent
	codec.Unmarshal(msgs[0].Payload, &decoded)
	if decoded.Intent != "move_left" || decoded.Confidence != 0.91 {
		t.Errorf("wrong intent data: %+v", decoded)
	}
	if len(auditLog.Entries()) < 2 {
		t.Errorf("expected >=2 audit entries, got %d", len(auditLog.Entries()))
	}
}

func TestToolRequest_PolicyEnforcement(t *testing.T) {
	auditLog := &memAuditLogger{}
	pe := policy.NewEngine(true, auditLog)
	pe.LoadSafeDefaults()
	safe := pe.Evaluate(policy.Request{Source: "eni", Action: "ui.cursor.move", Capability: "ui:control"})
	if !safe.Allowed {
		t.Error("safe action should be allowed")
	}
	restricted := pe.Evaluate(policy.Request{Source: "eni", Action: "system:reboot"})
	if restricted.Allowed || restricted.Verdict != policy.VerdictConfirm {
		t.Error("restricted action should require confirmation")
	}
}

func TestHMACIntegrity(t *testing.T) {
	key := []byte("eipc-shared-secret-for-testing!!")
	codec := protocol.DefaultCodec()
	hdr := protocol.Header{ServiceID: "eni.min", RequestID: "req-1", Sequence: 1, Timestamp: time.Now().UTC().Format(time.RFC3339Nano), Priority: uint8(core.PriorityP1)}
	hdrBytes, _ := codec.Marshal(hdr)
	intent := core.IntentEvent{Intent: "select", Confidence: 0.88}
	payload, _ := codec.Marshal(intent)
	frame := &protocol.Frame{Version: protocol.ProtocolVersion, MsgType: core.MsgTypeToByte(core.TypeIntent), Flags: protocol.FlagHMAC, Header: hdrBytes, Payload: payload}
	signable := frame.SignableBytes()
	frame.MAC = integrity.Sign(key, signable)
	if !integrity.Verify(key, signable, frame.MAC) {
		t.Fatal("valid frame should pass HMAC")
	}
	tamperedPayload := make([]byte, len(frame.Payload))
	copy(tamperedPayload, frame.Payload)
	tamperedPayload[0] = 'X'
	tf := &protocol.Frame{Version: frame.Version, MsgType: frame.MsgType, Flags: frame.Flags, Header: frame.Header, Payload: tamperedPayload, MAC: frame.MAC}
	if integrity.Verify(key, tf.SignableBytes(), tf.MAC) {
		t.Fatal("tampered frame should fail HMAC")
	}
}

func TestKeyring_SessionLifecycle(t *testing.T) {
	kr := keyring.New()
	entry, _ := kr.Generate("sess", 32, 1*time.Hour)
	data := []byte("payload")
	mac := integrity.Sign(entry.Key, data)
	if !integrity.Verify(entry.Key, data, mac) {
		t.Fatal("session key HMAC should verify")
	}
	newEntry, _ := kr.Rotate("sess", 32, 1*time.Hour)
	if integrity.Verify(newEntry.Key, data, mac) {
		t.Fatal("old MAC should fail with new key")
	}
}

func TestAuthentication_UnknownServiceRejected(t *testing.T) {
	a := auth.NewAuthenticator([]byte("secret"), map[string][]string{"eni.min": {"ui:control"}})
	peer, _ := a.Authenticate("eni.min")
	if _, err := a.ValidateSession(peer.SessionToken); err != nil {
		t.Fatal("valid session should validate")
	}
	if _, err := a.Authenticate("malicious"); err == nil {
		t.Fatal("unknown service should be rejected")
	}
	a.RevokeSession(peer.SessionToken)
	if _, err := a.ValidateSession(peer.SessionToken); err == nil {
		t.Fatal("revoked session should be rejected")
	}
}

func TestRouter_PriorityDispatch(t *testing.T) {
	router := core.NewRouter()
	var order []string
	var mu sync.Mutex
	router.Handle(core.TypeIntent, func(msg core.Message) (*core.Message, error) {
		mu.Lock()
		order = append(order, fmt.Sprintf("P%d", msg.Priority))
		mu.Unlock()
		return nil, nil
	})
	router.Handle(core.TypeFeatures, func(msg core.Message) (*core.Message, error) {
		mu.Lock()
		order = append(order, fmt.Sprintf("F%d", msg.Priority))
		mu.Unlock()
		return nil, nil
	})
	msgs := []core.Message{
		{Type: core.TypeFeatures, Priority: core.PriorityP2},
		{Type: core.TypeIntent, Priority: core.PriorityP0},
		{Type: core.TypeFeatures, Priority: core.PriorityP3},
	}
	router.DispatchBatch(msgs)
	if len(order) > 0 && order[0] != "P0" {
		t.Errorf("P0 should dispatch first, got %s", order[0])
	}
}

func TestHealth_HeartbeatMonitoring(t *testing.T) {
	h := health.NewService(100*time.Millisecond, 200*time.Millisecond)
	h.RecordHeartbeat("eni.min", "ready")
	if !h.IsAlive("eni.min") {
		t.Error("should be alive")
	}
	time.Sleep(250 * time.Millisecond)
	if h.IsAlive("eni.min") {
		t.Error("should be dead after timeout")
	}
}

func TestEndToEnd_SecureMinimalFlow(t *testing.T) {
	hmacKey := []byte("e2e-test-secret-key-32-bytes!!!")
	auditLog := &memAuditLogger{}
	a := auth.NewAuthenticator(hmacKey, map[string][]string{"eni.min": {"ui:control"}})
	capChecker := capability.NewChecker(map[string][]string{"ui:control": {"ui.cursor.move"}})
	pe := policy.NewEngine(true, auditLog)
	pe.LoadSafeDefaults()

	eniPeer, _ := a.Authenticate("eni.min")
	intentPayload, _ := json.Marshal(core.IntentEvent{Intent: "move_left", Confidence: 0.91})
	frame := &protocol.Frame{Version: protocol.ProtocolVersion, MsgType: core.MsgTypeToByte(core.TypeIntent), Flags: protocol.FlagHMAC, Header: []byte(`{"service_id":"eni.min","request_id":"req-e2e"}`), Payload: intentPayload}
	frame.MAC = integrity.Sign(hmacKey, frame.SignableBytes())
	if !integrity.Verify(hmacKey, frame.SignableBytes(), frame.MAC) {
		t.Fatal("MAC verification failed")
	}
	var ri core.IntentEvent
	json.Unmarshal(frame.Payload, &ri)
	if ri.Intent != "move_left" {
		t.Fatalf("wrong intent: %s", ri.Intent)
	}
	if err := capChecker.Check(eniPeer.Capabilities, "ui.cursor.move"); err != nil {
		t.Fatalf("cap check failed: %v", err)
	}
	pr := pe.Evaluate(policy.Request{Source: "eni.min", Action: "ui.cursor.move", Capability: "ui:control", RequestID: "req-e2e"})
	if !pr.Allowed {
		t.Fatalf("policy denied: %s", pr.Reason)
	}
	auditLog.Log(audit.Entry{RequestID: "req-e2e", Source: "eni.min", Target: "eai.min.agent", Action: "ui.cursor.move", Decision: "allow", Result: "success"})
	found := false
	for _, e := range auditLog.Entries() {
		if e.RequestID == "req-e2e" && e.Result == "success" {
			found = true
		}
	}
	if !found {
		t.Fatal("audit entry not found")
	}
	ackPayload, _ := json.Marshal(core.AckEvent{RequestID: "req-e2e", Status: "ok"})
	ackFrame := &protocol.Frame{Version: protocol.ProtocolVersion, MsgType: core.MsgTypeToByte(core.TypeAck), Flags: protocol.FlagHMAC, Header: []byte(`{"service_id":"eai.min.agent"}`), Payload: ackPayload}
	ackFrame.MAC = integrity.Sign(hmacKey, ackFrame.SignableBytes())
	if !integrity.Verify(hmacKey, ackFrame.SignableBytes(), ackFrame.MAC) {
		t.Fatal("ack MAC failed")
	}
}

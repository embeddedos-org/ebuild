// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"time"

	"github.com/embeddedos-org/eipc/core"
	"github.com/embeddedos-org/eipc/protocol"
	"github.com/embeddedos-org/eipc/transport/tcp"
)

func main() {
	addr := "127.0.0.1:9090"
	if len(os.Args) > 1 {
		addr = os.Args[1]
	}

	sharedSecret := []byte("eipc-demo-shared-secret-32bytes!")
	serviceID := "nia.min"
	codec := protocol.DefaultCodec()

	log.Printf("EIPC client connecting to %s as %s", addr, serviceID)

	transport := tcp.New()
	conn, err := transport.Dial(addr)
	if err != nil {
		log.Fatalf("dial: %v", err)
	}

	endpoint := core.NewClientEndpoint(conn, codec, sharedSecret, "")

	// Step 1: Authenticate
	log.Println("[1] Sending authentication request...")
	type authRequest struct {
		ServiceID string `json:"service_id"`
	}
	authPayload, _ := codec.Marshal(authRequest{ServiceID: serviceID})

	if err := endpoint.Send(core.Message{
		Version:   core.ProtocolVersion,
		Type:      core.TypeAck,
		Source:    serviceID,
		Timestamp: time.Now().UTC(),
		RequestID: "auth-1",
		Payload:   authPayload,
	}); err != nil {
		log.Fatalf("send auth: %v", err)
	}

	// Step 2: Receive session token
	authResp, err := endpoint.Receive()
	if err != nil {
		log.Fatalf("receive auth response: %v", err)
	}

	type authResponse struct {
		Status       string   `json:"status"`
		SessionToken string   `json:"session_token"`
		Capabilities []string `json:"capabilities"`
		Error        string   `json:"error,omitempty"`
	}
	var auth authResponse
	if err := json.Unmarshal(authResp.Payload, &auth); err != nil {
		log.Fatalf("unmarshal auth response: %v", err)
	}

	if auth.Status != "ok" {
		log.Fatalf("[AUTH] rejected: %s", auth.Error)
	}

	sessionToken := auth.SessionToken
	log.Printf("[2] Authenticated! token=%s...%s caps=%v",
		sessionToken[:8], sessionToken[len(sessionToken)-8:], auth.Capabilities)

	// Step 3: Send HMAC-protected intent
	log.Println("[3] Sending intent: move_left (confidence=0.91)")
	intentPayload, _ := codec.Marshal(core.IntentEvent{
		Intent:     "move_left",
		Confidence: 0.91,
		SessionID:  sessionToken,
	})

	if err := endpoint.Send(core.Message{
		Version:    core.ProtocolVersion,
		Type:       core.TypeIntent,
		Source:     serviceID,
		Timestamp:  time.Now().UTC(),
		SessionID:  sessionToken,
		RequestID:  "req-1",
		Priority:   core.PriorityP0,
		Capability: "ui:control",
		Payload:    intentPayload,
	}); err != nil {
		log.Fatalf("send intent: %v", err)
	}

	// Step 4: Receive ack
	ackMsg, err := endpoint.Receive()
	if err != nil {
		log.Fatalf("receive ack: %v", err)
	}

	var ack core.AckEvent
	if err := json.Unmarshal(ackMsg.Payload, &ack); err != nil {
		log.Fatalf("unmarshal ack: %v", err)
	}

	log.Printf("[4] Received ACK: request_id=%s status=%s", ack.RequestID, ack.Status)

	// Step 5: Send a second intent
	log.Println("[5] Sending intent: select_item (confidence=0.88)")
	intent2Payload, _ := codec.Marshal(core.IntentEvent{
		Intent:     "select_item",
		Confidence: 0.88,
		SessionID:  sessionToken,
	})

	if err := endpoint.Send(core.Message{
		Version:    core.ProtocolVersion,
		Type:       core.TypeIntent,
		Source:     serviceID,
		Timestamp:  time.Now().UTC(),
		SessionID:  sessionToken,
		RequestID:  "req-2",
		Priority:   core.PriorityP1,
		Capability: "ui:control",
		Payload:    intent2Payload,
	}); err != nil {
		log.Fatalf("send intent 2: %v", err)
	}

	ack2Msg, err := endpoint.Receive()
	if err != nil {
		log.Fatalf("receive ack 2: %v", err)
	}

	var ack2 core.AckEvent
	if err := json.Unmarshal(ack2Msg.Payload, &ack2); err != nil {
		log.Fatalf("unmarshal ack 2: %v", err)
	}

	log.Printf("[6] Received ACK: request_id=%s status=%s", ack2.RequestID, ack2.Status)

	// Step 6: Send heartbeat
	log.Println("[7] Sending heartbeat...")
	hbPayload, _ := codec.Marshal(core.HeartbeatEvent{
		Service: serviceID,
		Status:  "ready",
	})

	if err := endpoint.Send(core.Message{
		Version:   core.ProtocolVersion,
		Type:      core.TypeHeartbeat,
		Source:    serviceID,
		Timestamp: time.Now().UTC(),
		SessionID: sessionToken,
		RequestID: "hb-1",
		Priority:  core.PriorityP2,
		Payload:   hbPayload,
	}); err != nil {
		log.Fatalf("send heartbeat: %v", err)
	}

	// Brief pause to let server process
	time.Sleep(100 * time.Millisecond)

	endpoint.Close()
	fmt.Println()
	fmt.Println("=== EIPC Demo Complete ===")
	fmt.Println("End-to-end flow demonstrated:")
	fmt.Println("  1. Client connected to server")
	fmt.Println("  2. Server validated peer identity (nia.min)")
	fmt.Println("  3. Server issued session token")
	fmt.Println("  4. Client sent HMAC-protected intents")
	fmt.Println("  5. Server checked capability (ui:control)")
	fmt.Println("  6. Server processed requests")
	fmt.Println("  7. Audit events recorded")
	fmt.Println("  8. Acks returned to client")
}

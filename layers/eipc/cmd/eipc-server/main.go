// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package main

import (
	"encoding/json"
	"fmt"
	"log"
	"os"
	"os/signal"
	"time"

	"github.com/embeddedos-org/eipc/core"
	"github.com/embeddedos-org/eipc/protocol"
	"github.com/embeddedos-org/eipc/security/auth"
	"github.com/embeddedos-org/eipc/security/capability"
	"github.com/embeddedos-org/eipc/services/audit"
	"github.com/embeddedos-org/eipc/services/health"
	"github.com/embeddedos-org/eipc/services/registry"
	"github.com/embeddedos-org/eipc/transport"
	"github.com/embeddedos-org/eipc/transport/tcp"
)

func main() {
	addr := "127.0.0.1:9090"
	if len(os.Args) > 1 {
		addr = os.Args[1]
	}

	sharedSecret := []byte("eipc-demo-shared-secret-32bytes!")

	authenticator := auth.NewAuthenticator(sharedSecret, map[string][]string{
		"nia.min":           {"ui:control", "device:read"},
		"nia.framework":     {"ui:control", "device:read", "device:write"},
		"ail.min.agent":     {"ui:control"},
		"ail.framework":     {"ui:control", "device:read", "device:write", "system:restricted"},
	})

	capChecker := capability.NewChecker(map[string][]string{
		"ui:control":       {"ui.cursor.move", "ui.click", "ui.scroll"},
		"device:read":      {"device.sensor.read", "device.status"},
		"device:write":     {"device.actuator.write"},
		"system:restricted": {"system.reboot", "system.update"},
	})

	auditLogger, err := audit.NewFileLogger("")
	if err != nil {
		log.Fatalf("audit logger: %v", err)
	}
	defer auditLogger.Close()

	healthSvc := health.NewService(5*time.Second, 15*time.Second)

	reg := registry.NewRegistry()
	_ = reg.Register(registry.ServiceInfo{
		ServiceID:    "eipc-server",
		Capabilities: []string{"ui:control", "device:read", "device:write"},
		Versions:     []uint16{1},
		MessageTypes: []core.MessageType{core.TypeIntent, core.TypeAck, core.TypeHeartbeat, core.TypeAudit},
		Priority:     core.PriorityP0,
	})

	router := core.NewRouter()

	router.Handle(core.TypeIntent, func(msg core.Message) (*core.Message, error) {
		var intent core.IntentEvent
		codec := protocol.DefaultCodec()
		if err := codec.Unmarshal(msg.Payload, &intent); err != nil {
			return nil, fmt.Errorf("unmarshal intent: %w", err)
		}

		log.Printf("[INTENT] from=%s intent=%s confidence=%.2f session=%s",
			msg.Source, intent.Intent, intent.Confidence, intent.SessionID)

		if err := capChecker.Check([]string{msg.Capability}, "ui.cursor.move"); err != nil {
			log.Printf("[POLICY] DENIED: %v", err)
			_ = auditLogger.Log(audit.Entry{
				RequestID: msg.RequestID,
				Source:    msg.Source,
				Target:    "eipc-server",
				Action:    intent.Intent,
				Decision:  "denied",
				Result:    err.Error(),
			})
			return nil, err
		}

		log.Printf("[POLICY] ALLOWED: capability=%s action=%s", msg.Capability, intent.Intent)

		_ = auditLogger.Log(audit.Entry{
			RequestID: msg.RequestID,
			Source:    msg.Source,
			Target:    "eipc-server",
			Action:    intent.Intent,
			Decision:  "allowed",
			Result:    "success",
		})

		ackPayload, _ := codec.Marshal(core.AckEvent{
			RequestID: msg.RequestID,
			Status:    "ok",
		})

		ack := core.Message{
			Version:   core.ProtocolVersion,
			Type:      core.TypeAck,
			Source:    "eipc-server",
			Timestamp: time.Now().UTC(),
			SessionID: msg.SessionID,
			RequestID: msg.RequestID,
			Priority:  core.PriorityP0,
			Payload:   ackPayload,
		}
		return &ack, nil
	})

	router.Handle(core.TypeHeartbeat, func(msg core.Message) (*core.Message, error) {
		var hb core.HeartbeatEvent
		codec := protocol.DefaultCodec()
		if err := codec.Unmarshal(msg.Payload, &hb); err != nil {
			return nil, err
		}
		healthSvc.RecordHeartbeat(hb.Service, hb.Status)
		log.Printf("[HEARTBEAT] service=%s status=%s", hb.Service, hb.Status)
		return nil, nil
	})

	tcpTransport := tcp.New()
	if err := tcpTransport.Listen(addr); err != nil {
		log.Fatalf("listen: %v", err)
	}
	defer tcpTransport.Close()

	log.Printf("EIPC server listening on %s", tcpTransport.Addr())

	go func() {
		sigCh := make(chan os.Signal, 1)
		signal.Notify(sigCh, os.Interrupt)
		<-sigCh
		log.Println("Shutting down...")
		tcpTransport.Close()
		os.Exit(0)
	}()

	codec := protocol.DefaultCodec()

	for {
		conn, err := tcpTransport.Accept()
		if err != nil {
			log.Printf("accept error: %v", err)
			return
		}

		go handleConnection(conn, authenticator, codec, sharedSecret, router, auditLogger)
	}
}

func handleConnection(
	conn transport.Connection,
	authenticator *auth.Authenticator,
	codec protocol.Codec,
	hmacKey []byte,
	router *core.Router,
	auditLogger audit.Logger,
) {
	defer conn.Close()
	log.Printf("[CONN] new connection from %s", conn.RemoteAddr())

	endpoint := core.NewServerEndpoint(conn, codec, hmacKey)

	authMsg, err := endpoint.Receive()
	if err != nil {
		log.Printf("[AUTH] failed to receive auth message: %v", err)
		return
	}

	type authRequest struct {
		ServiceID string `json:"service_id"`
	}
	var authReq authRequest
	if err := json.Unmarshal(authMsg.Payload, &authReq); err != nil {
		log.Printf("[AUTH] bad auth payload: %v", err)
		return
	}

	peer, err := authenticator.Authenticate(authReq.ServiceID)
	if err != nil {
		log.Printf("[AUTH] REJECTED: %v", err)

		type authResponse struct {
			Status string `json:"status"`
			Error  string `json:"error,omitempty"`
		}
		respPayload, _ := codec.Marshal(authResponse{Status: "denied", Error: err.Error()})
		_ = endpoint.Send(core.Message{
			Version:   core.ProtocolVersion,
			Type:      core.TypeAck,
			Source:    "eipc-server",
			Timestamp: time.Now().UTC(),
			RequestID: authMsg.RequestID,
			Payload:   respPayload,
		})
		return
	}

	log.Printf("[AUTH] ACCEPTED: service=%s token=%s...%s caps=%v",
		peer.ServiceID, peer.SessionToken[:8], peer.SessionToken[len(peer.SessionToken)-8:], peer.Capabilities)

	type authResponse struct {
		Status       string   `json:"status"`
		SessionToken string   `json:"session_token"`
		Capabilities []string `json:"capabilities"`
	}
	respPayload, _ := codec.Marshal(authResponse{
		Status:       "ok",
		SessionToken: peer.SessionToken,
		Capabilities: peer.Capabilities,
	})
	if err := endpoint.Send(core.Message{
		Version:   core.ProtocolVersion,
		Type:      core.TypeAck,
		Source:    "eipc-server",
		Timestamp: time.Now().UTC(),
		RequestID: authMsg.RequestID,
		Payload:   respPayload,
	}); err != nil {
		log.Printf("[AUTH] failed to send auth response: %v", err)
		return
	}

	for {
		msg, err := endpoint.Receive()
		if err != nil {
			log.Printf("[CONN] connection closed: %v", err)
			return
		}

		resp, err := router.Dispatch(msg)
		if err != nil {
			log.Printf("[DISPATCH] error: %v", err)
			errPayload, _ := codec.Marshal(core.AckEvent{
				RequestID: msg.RequestID,
				Status:    "error",
				Error:     err.Error(),
			})
			_ = endpoint.Send(core.Message{
				Version:   core.ProtocolVersion,
				Type:      core.TypeAck,
				Source:    "eipc-server",
				Timestamp: time.Now().UTC(),
				SessionID: msg.SessionID,
				RequestID: msg.RequestID,
				Priority:  core.PriorityP0,
				Payload:   errPayload,
			})
			continue
		}

		if resp != nil {
			if err := endpoint.Send(*resp); err != nil {
				log.Printf("[SEND] error: %v", err)
				return
			}
		}
	}
}

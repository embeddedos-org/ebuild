// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package core

import (
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	"github.com/embeddedos-org/eipc/protocol"
	"github.com/embeddedos-org/eipc/security/integrity"
	"github.com/embeddedos-org/eipc/security/replay"
	"github.com/embeddedos-org/eipc/transport"
)

// Endpoint is the Go API surface for sending/receiving EIPC messages.
type Endpoint interface {
	Send(msg Message) error
	Receive() (Message, error)
	Close() error
}

// ClientEndpoint connects to an EIPC server and exchanges messages.
type ClientEndpoint struct {
	conn      transport.Connection
	codec     protocol.Codec
	hmacKey   []byte
	sessionID string
	sequence  atomic.Uint64
}

// NewClientEndpoint creates a client endpoint over an existing connection.
func NewClientEndpoint(conn transport.Connection, codec protocol.Codec, hmacKey []byte, sessionID string) *ClientEndpoint {
	return &ClientEndpoint{
		conn:      conn,
		codec:     codec,
		hmacKey:   hmacKey,
		sessionID: sessionID,
	}
}

func (e *ClientEndpoint) Send(msg Message) error {
	seq := e.sequence.Add(1)

	hdr := protocol.Header{
		ServiceID:     msg.Source,
		SessionID:     msg.SessionID,
		RequestID:     msg.RequestID,
		Sequence:      seq,
		Timestamp:     msg.Timestamp.Format(time.RFC3339Nano),
		Priority:      uint8(msg.Priority),
		Capability:    msg.Capability,
		PayloadFormat: uint8(PayloadJSON),
	}
	hdrBytes, err := e.codec.Marshal(hdr)
	if err != nil {
		return fmt.Errorf("marshal header: %w", err)
	}

	frame := &protocol.Frame{
		Version: ProtocolVersion,
		MsgType: MsgTypeToByte(msg.Type),
		Flags:   protocol.FlagHMAC,
		Header:  hdrBytes,
		Payload: msg.Payload,
	}

	frame.MAC = integrity.Sign(e.hmacKey, frame.SignableBytes())

	return e.conn.Send(frame)
}

func (e *ClientEndpoint) Receive() (Message, error) {
	frame, err := e.conn.Receive()
	if err != nil {
		return Message{}, err
	}

	if frame.Flags&protocol.FlagHMAC != 0 {
		if !integrity.Verify(e.hmacKey, frame.SignableBytes(), frame.MAC) {
			return Message{}, ErrIntegrity
		}
	}

	var hdr protocol.Header
	if err := e.codec.Unmarshal(frame.Header, &hdr); err != nil {
		return Message{}, fmt.Errorf("unmarshal header: %w", err)
	}

	ts, _ := time.Parse(time.RFC3339Nano, hdr.Timestamp)

	return Message{
		Version:    frame.Version,
		Type:       msgTypeFromByte(frame.MsgType),
		Source:     hdr.ServiceID,
		Timestamp:  ts,
		SessionID:  hdr.SessionID,
		RequestID:  hdr.RequestID,
		Priority:   Priority(hdr.Priority),
		Capability: hdr.Capability,
		Payload:    frame.Payload,
	}, nil
}

func (e *ClientEndpoint) Close() error {
	return e.conn.Close()
}

// ServerEndpoint handles a single server-side connection.
type ServerEndpoint struct {
	conn    transport.Connection
	codec   protocol.Codec
	hmacKey []byte
	replay  *replay.Tracker
	sendMu  sync.Mutex
	seq     atomic.Uint64
}

// NewServerEndpoint wraps a server-side connection.
func NewServerEndpoint(conn transport.Connection, codec protocol.Codec, hmacKey []byte) *ServerEndpoint {
	return &ServerEndpoint{
		conn:    conn,
		codec:   codec,
		hmacKey: hmacKey,
		replay:  replay.NewTracker(0),
	}
}

func (e *ServerEndpoint) Send(msg Message) error {
	seq := e.seq.Add(1)

	hdr := protocol.Header{
		ServiceID:     msg.Source,
		SessionID:     msg.SessionID,
		RequestID:     msg.RequestID,
		Sequence:      seq,
		Timestamp:     msg.Timestamp.Format(time.RFC3339Nano),
		Priority:      uint8(msg.Priority),
		Capability:    msg.Capability,
		PayloadFormat: uint8(PayloadJSON),
	}
	hdrBytes, err := e.codec.Marshal(hdr)
	if err != nil {
		return fmt.Errorf("marshal header: %w", err)
	}

	frame := &protocol.Frame{
		Version: ProtocolVersion,
		MsgType: MsgTypeToByte(msg.Type),
		Flags:   protocol.FlagHMAC,
		Header:  hdrBytes,
		Payload: msg.Payload,
	}

	frame.MAC = integrity.Sign(e.hmacKey, frame.SignableBytes())

	return e.conn.Send(frame)
}

func (e *ServerEndpoint) Receive() (Message, error) {
	frame, err := e.conn.Receive()
	if err != nil {
		return Message{}, err
	}

	if frame.Flags&protocol.FlagHMAC != 0 {
		if !integrity.Verify(e.hmacKey, frame.SignableBytes(), frame.MAC) {
			return Message{}, ErrIntegrity
		}
	}

	var hdr protocol.Header
	if err := e.codec.Unmarshal(frame.Header, &hdr); err != nil {
		return Message{}, fmt.Errorf("unmarshal header: %w", err)
	}

	if err := e.replay.Check(hdr.Sequence); err != nil {
		return Message{}, err
	}

	ts, _ := time.Parse(time.RFC3339Nano, hdr.Timestamp)

	return Message{
		Version:    frame.Version,
		Type:       msgTypeFromByte(frame.MsgType),
		Source:     hdr.ServiceID,
		Timestamp:  ts,
		SessionID:  hdr.SessionID,
		RequestID:  hdr.RequestID,
		Priority:   Priority(hdr.Priority),
		Capability: hdr.Capability,
		Payload:    frame.Payload,
	}, nil
}

func (e *ServerEndpoint) Close() error {
	return e.conn.Close()
}

// RemoteAddr returns the remote address of the underlying connection.
func (e *ServerEndpoint) RemoteAddr() string {
	return e.conn.RemoteAddr()
}

func msgTypeFromByte(b uint8) MessageType {
	switch b {
	case 'i':
		return TypeIntent
	case 'f':
		return TypeFeatures
	case 't':
		return TypeToolRequest
	case 'a':
		return TypeAck
	case 'p':
		return TypePolicyResult
	case 'h':
		return TypeHeartbeat
	case 'u':
		return TypeAudit
	default:
		return MessageType(string(rune(b)))
	}
}

// MsgTypeToByte converts a MessageType to its wire byte representation.
func MsgTypeToByte(mt MessageType) uint8 {
	switch mt {
	case TypeIntent:
		return 'i'
	case TypeFeatures:
		return 'f'
	case TypeToolRequest:
		return 't'
	case TypeAck:
		return 'a'
	case TypePolicyResult:
		return 'p'
	case TypeHeartbeat:
		return 'h'
	case TypeAudit:
		return 'u'
	default:
		if len(mt) > 0 {
			return mt[0]
		}
		return 0
	}
}

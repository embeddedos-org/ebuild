// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package transport

import (
	"encoding/binary"
	"fmt"
	"io"
	"net"

	"github.com/embeddedos-org/eipc/protocol"
)

// Transport is the pluggable transport abstraction for EIPC.
type Transport interface {
	// Listen starts accepting connections on the transport.
	Listen(address string) error
	// Dial connects to a remote transport endpoint.
	Dial(address string) (Connection, error)
	// Accept waits for and returns the next inbound connection.
	Accept() (Connection, error)
	// Close shuts down the transport listener.
	Close() error
}

// Connection represents a single bidirectional EIPC link.
type Connection interface {
	// Send encodes and transmits a frame.
	Send(frame *protocol.Frame) error
	// Receive reads and decodes the next frame.
	Receive() (*protocol.Frame, error)
	// RemoteAddr returns the remote address of the connection.
	RemoteAddr() string
	// Close shuts down the connection.
	Close() error
}

// ConnWrapper wraps a net.Conn with length-prefixed frame I/O.
type ConnWrapper struct {
	conn net.Conn
}

// NewConnWrapper wraps an existing net.Conn for EIPC frame transport.
func NewConnWrapper(conn net.Conn) *ConnWrapper {
	return &ConnWrapper{conn: conn}
}

// Send writes a length-prefixed frame to the connection.
func (c *ConnWrapper) Send(frame *protocol.Frame) error {
	var frameBuf []byte
	{
		// Encode frame to intermediate buffer to get length
		buf := &limitedBuffer{}
		if err := frame.Encode(buf); err != nil {
			return fmt.Errorf("encode frame: %w", err)
		}
		frameBuf = buf.Bytes()
	}

	// Write 4-byte length prefix
	lenBuf := make([]byte, 4)
	binary.BigEndian.PutUint32(lenBuf, uint32(len(frameBuf)))
	if _, err := c.conn.Write(lenBuf); err != nil {
		return fmt.Errorf("write length: %w", err)
	}
	if _, err := c.conn.Write(frameBuf); err != nil {
		return fmt.Errorf("write frame: %w", err)
	}
	return nil
}

// Receive reads a length-prefixed frame from the connection.
func (c *ConnWrapper) Receive() (*protocol.Frame, error) {
	lenBuf := make([]byte, 4)
	if _, err := io.ReadFull(c.conn, lenBuf); err != nil {
		return nil, fmt.Errorf("read length: %w", err)
	}
	frameLen := binary.BigEndian.Uint32(lenBuf)
	if frameLen > protocol.MaxFrameSize {
		return nil, fmt.Errorf("frame too large: %d bytes", frameLen)
	}

	frameBuf := make([]byte, frameLen)
	if _, err := io.ReadFull(c.conn, frameBuf); err != nil {
		return nil, fmt.Errorf("read frame: %w", err)
	}

	return protocol.Decode(io.Reader(newBytesReader(frameBuf)))
}

// RemoteAddr returns the remote address string.
func (c *ConnWrapper) RemoteAddr() string {
	return c.conn.RemoteAddr().String()
}

// Close closes the underlying connection.
func (c *ConnWrapper) Close() error {
	return c.conn.Close()
}

// limitedBuffer is a simple bytes.Buffer replacement to avoid import cycle issues.
type limitedBuffer struct {
	data []byte
}

func (b *limitedBuffer) Write(p []byte) (int, error) {
	b.data = append(b.data, p...)
	return len(p), nil
}

func (b *limitedBuffer) Bytes() []byte {
	return b.data
}

// bytesReader wraps a byte slice as an io.Reader.
type bytesReader struct {
	data []byte
	pos  int
}

func newBytesReader(data []byte) *bytesReader {
	return &bytesReader{data: data}
}

func (r *bytesReader) Read(p []byte) (int, error) {
	if r.pos >= len(r.data) {
		return 0, io.EOF
	}
	n := copy(p, r.data[r.pos:])
	r.pos += n
	return n, nil
}

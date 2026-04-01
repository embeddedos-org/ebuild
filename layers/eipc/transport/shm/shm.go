// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package shm

import (
	"fmt"
	"runtime"
	"sync"
	"sync/atomic"

	"github.com/embeddedos-org/eipc/protocol"
	"github.com/embeddedos-org/eipc/transport"
)

// Config holds shared memory transport configuration.
type Config struct {
	Name       string // Shared memory region name
	BufferSize int    // Ring buffer size in bytes (default 64KB)
	SlotCount  int    // Number of message slots (default 256)
}

const (
	DefaultBufferSize = 64 * 1024
	DefaultSlotCount  = 256
	MaxSlotSize       = 8192
)

// RingBuffer is an in-process shared memory ring buffer for
// high-rate feature streams between ENI and EAI.
//
// This is a process-local implementation suitable for threads/goroutines.
// For true cross-process shared memory, the platform-specific mmap
// implementation should be used (see shm_linux.go, shm_windows.go).
type RingBuffer struct {
	mu       sync.Mutex
	name     string
	buf      []byte
	slots    int
	slotSize int
	head     atomic.Uint64
	tail     atomic.Uint64
}

// NewRingBuffer creates a new shared-memory ring buffer.
func NewRingBuffer(cfg Config) *RingBuffer {
	if cfg.BufferSize <= 0 {
		cfg.BufferSize = DefaultBufferSize
	}
	if cfg.SlotCount <= 0 {
		cfg.SlotCount = DefaultSlotCount
	}
	slotSize := cfg.BufferSize / cfg.SlotCount
	if slotSize > MaxSlotSize {
		slotSize = MaxSlotSize
	}

	return &RingBuffer{
		name:     cfg.Name,
		buf:      make([]byte, cfg.SlotCount*slotSize),
		slots:    cfg.SlotCount,
		slotSize: slotSize,
	}
}

// Write places a frame into the next available slot.
// Returns ErrBackpressure if the buffer is full.
func (rb *RingBuffer) Write(frame *protocol.Frame) error {
	data := make([]byte, 0, protocol.FrameFixedSize+len(frame.Header)+len(frame.Payload))
	data = append(data, frame.SignableBytes()...)
	if len(data) > rb.slotSize-2 {
		return fmt.Errorf("frame too large for slot (%d > %d)", len(data), rb.slotSize-2)
	}

	head := rb.head.Load()
	tail := rb.tail.Load()

	if head-tail >= uint64(rb.slots) {
		return fmt.Errorf("ring buffer full (backpressure)")
	}

	idx := int(head % uint64(rb.slots))
	offset := idx * rb.slotSize

	rb.mu.Lock()
	rb.buf[offset] = byte(len(data) >> 8)
	rb.buf[offset+1] = byte(len(data))
	copy(rb.buf[offset+2:], data)
	rb.mu.Unlock()

	rb.head.Add(1)
	return nil
}

// Read retrieves the next frame from the buffer.
// Returns nil if the buffer is empty.
func (rb *RingBuffer) Read() (*protocol.Frame, error) {
	head := rb.head.Load()
	tail := rb.tail.Load()

	if tail >= head {
		return nil, nil
	}

	idx := int(tail % uint64(rb.slots))
	offset := idx * rb.slotSize

	rb.mu.Lock()
	length := int(rb.buf[offset])<<8 | int(rb.buf[offset+1])
	data := make([]byte, length)
	copy(data, rb.buf[offset+2:offset+2+length])
	rb.mu.Unlock()

	rb.tail.Add(1)

	if length < protocol.FrameFixedSize {
		return nil, fmt.Errorf("slot data too short (%d bytes)", length)
	}

	frame := &protocol.Frame{
		Version: uint16(data[4])<<8 | uint16(data[5]),
		MsgType: data[6],
		Flags:   data[7],
	}

	headerLen := int(data[8])<<24 | int(data[9])<<16 | int(data[10])<<8 | int(data[11])
	payloadLen := int(data[12])<<24 | int(data[13])<<16 | int(data[14])<<8 | int(data[15])

	pos := protocol.FrameFixedSize
	if headerLen > 0 && pos+headerLen <= length {
		frame.Header = make([]byte, headerLen)
		copy(frame.Header, data[pos:pos+headerLen])
		pos += headerLen
	}
	if payloadLen > 0 && pos+payloadLen <= length {
		frame.Payload = make([]byte, payloadLen)
		copy(frame.Payload, data[pos:pos+payloadLen])
	}

	return frame, nil
}

// Len returns the number of unread messages in the buffer.
func (rb *RingBuffer) Len() int {
	return int(rb.head.Load() - rb.tail.Load())
}

// Name returns the shared memory region name.
func (rb *RingBuffer) Name() string {
	return rb.name
}

// Connection wraps a RingBuffer pair (tx/rx) as a transport.Connection.
type Connection struct {
	tx     *RingBuffer
	rx     *RingBuffer
	remote string
	codec  protocol.Codec
}

// NewConnection creates a shared-memory connection using two ring buffers.
func NewConnection(tx, rx *RingBuffer, remote string) *Connection {
	return &Connection{
		tx:     tx,
		rx:     rx,
		remote: remote,
		codec:  protocol.DefaultCodec(),
	}
}

func (c *Connection) Send(frame *protocol.Frame) error {
	return c.tx.Write(frame)
}

func (c *Connection) Receive() (*protocol.Frame, error) {
	for {
		frame, err := c.rx.Read()
		if err != nil {
			return nil, err
		}
		if frame != nil {
			return frame, nil
		}
		runtime.Gosched()
	}
}

func (c *Connection) Close() error {
	return nil
}

func (c *Connection) RemoteAddr() string {
	return c.remote
}

// Ensure Connection satisfies transport.Connection.
var _ transport.Connection = (*Connection)(nil)

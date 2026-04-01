// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package protocol

import (
	"encoding/binary"
	"errors"
	"fmt"
	"io"
)

// Magic bytes: "EIPC" = 0x45495043
const (
	MagicBytes      uint32 = 0x45495043
	MaxFrameSize    uint32 = 1 << 20 // 1 MB
	MACSize                = 32      // HMAC-SHA256
	ProtocolVersion uint16 = 1
)

var (
	ErrBadMagic      = errors.New("eipc: invalid magic bytes")
	ErrBadVersion    = errors.New("eipc: unsupported protocol version")
	ErrFrameTooLarge = errors.New("eipc: frame exceeds maximum size")
)

// Frame flags
const (
	FlagHMAC     uint8 = 1 << 0 // Frame carries an HMAC
	FlagCompress uint8 = 1 << 1 // Payload is compressed (future)
)

// Frame is the on-the-wire representation of an EIPC message.
//
// Wire format:
//
//	[magic:4][version:2][msg_type:1][flags:1][header_len:4][payload_len:4][header][payload][mac:32?]
type Frame struct {
	Version uint16
	MsgType uint8
	Flags   uint8
	Header  []byte
	Payload []byte
	MAC     []byte // Present only when FlagHMAC is set
}

// FrameFixedSize is the byte count of the fixed-width preamble.
const FrameFixedSize = 4 + 2 + 1 + 1 + 4 + 4 // 16 bytes

// Encode writes the frame to w in the EIPC wire format.
func (f *Frame) Encode(w io.Writer) error {
	buf := make([]byte, FrameFixedSize)
	binary.BigEndian.PutUint32(buf[0:4], MagicBytes)
	binary.BigEndian.PutUint16(buf[4:6], f.Version)
	buf[6] = f.MsgType
	buf[7] = f.Flags
	binary.BigEndian.PutUint32(buf[8:12], uint32(len(f.Header)))
	binary.BigEndian.PutUint32(buf[12:16], uint32(len(f.Payload)))

	if _, err := w.Write(buf); err != nil {
		return fmt.Errorf("write preamble: %w", err)
	}
	if _, err := w.Write(f.Header); err != nil {
		return fmt.Errorf("write header: %w", err)
	}
	if _, err := w.Write(f.Payload); err != nil {
		return fmt.Errorf("write payload: %w", err)
	}
	if f.Flags&FlagHMAC != 0 && len(f.MAC) == MACSize {
		if _, err := w.Write(f.MAC); err != nil {
			return fmt.Errorf("write mac: %w", err)
		}
	}
	return nil
}

// Decode reads a frame from r in the EIPC wire format.
func Decode(r io.Reader) (*Frame, error) {
	preamble := make([]byte, FrameFixedSize)
	if _, err := io.ReadFull(r, preamble); err != nil {
		return nil, fmt.Errorf("read preamble: %w", err)
	}

	magic := binary.BigEndian.Uint32(preamble[0:4])
	if magic != MagicBytes {
		return nil, ErrBadMagic
	}

	version := binary.BigEndian.Uint16(preamble[4:6])
	if version != ProtocolVersion {
		return nil, ErrBadVersion
	}

	f := &Frame{
		Version: version,
		MsgType: preamble[6],
		Flags:   preamble[7],
	}

	headerLen := binary.BigEndian.Uint32(preamble[8:12])
	payloadLen := binary.BigEndian.Uint32(preamble[12:16])

	totalLen := headerLen + payloadLen
	if totalLen > MaxFrameSize {
		return nil, ErrFrameTooLarge
	}

	if headerLen > 0 {
		f.Header = make([]byte, headerLen)
		if _, err := io.ReadFull(r, f.Header); err != nil {
			return nil, fmt.Errorf("read header: %w", err)
		}
	}

	if payloadLen > 0 {
		f.Payload = make([]byte, payloadLen)
		if _, err := io.ReadFull(r, f.Payload); err != nil {
			return nil, fmt.Errorf("read payload: %w", err)
		}
	}

	if f.Flags&FlagHMAC != 0 {
		f.MAC = make([]byte, MACSize)
		if _, err := io.ReadFull(r, f.MAC); err != nil {
			return nil, fmt.Errorf("read mac: %w", err)
		}
	}

	return f, nil
}

// SignableBytes returns the portion of the frame that is covered by the MAC
// (everything except the MAC itself).
func (f *Frame) SignableBytes() []byte {
	size := FrameFixedSize + len(f.Header) + len(f.Payload)
	buf := make([]byte, 0, size)

	preamble := make([]byte, FrameFixedSize)
	binary.BigEndian.PutUint32(preamble[0:4], MagicBytes)
	binary.BigEndian.PutUint16(preamble[4:6], f.Version)
	preamble[6] = f.MsgType
	preamble[7] = f.Flags
	binary.BigEndian.PutUint32(preamble[8:12], uint32(len(f.Header)))
	binary.BigEndian.PutUint32(preamble[12:16], uint32(len(f.Payload)))

	buf = append(buf, preamble...)
	buf = append(buf, f.Header...)
	buf = append(buf, f.Payload...)
	return buf
}

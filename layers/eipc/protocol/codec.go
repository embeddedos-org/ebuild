// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package protocol

import "encoding/json"

// Codec serializes and deserializes message payloads.
type Codec interface {
	Marshal(v interface{}) ([]byte, error)
	Unmarshal(data []byte, v interface{}) error
}

// JSONCodec implements Codec using JSON encoding.
type JSONCodec struct{}

func (JSONCodec) Marshal(v interface{}) ([]byte, error) {
	return json.Marshal(v)
}

func (JSONCodec) Unmarshal(data []byte, v interface{}) error {
	return json.Unmarshal(data, v)
}

// DefaultCodec returns the development-mode codec (JSON).
func DefaultCodec() Codec {
	return JSONCodec{}
}

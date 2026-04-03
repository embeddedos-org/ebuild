// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package integrity

import (
	"crypto/hmac"
	"crypto/sha256"
)

// Sign computes HMAC-SHA256 over data using the given key.
func Sign(key, data []byte) []byte {
	mac := hmac.New(sha256.New, key)
	mac.Write(data)
	return mac.Sum(nil)
}

// Verify checks that the provided mac matches the HMAC-SHA256 of data under key.
func Verify(key, data, mac []byte) bool {
	expected := Sign(key, data)
	return hmac.Equal(expected, mac)
}

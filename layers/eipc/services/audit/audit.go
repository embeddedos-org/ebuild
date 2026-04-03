// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project

package audit

import (
	"encoding/json"
	"fmt"
	"io"
	"os"
	"sync"
	"time"
)

// Logger defines the audit logging interface.
type Logger interface {
	Log(entry Entry) error
	Close() error
}

// Entry is a single audit log record.
type Entry struct {
	Timestamp  string `json:"timestamp"`
	RequestID  string `json:"request_id"`
	Source     string `json:"source"`
	Target     string `json:"target"`
	Action     string `json:"action"`
	Decision   string `json:"decision"`
	Result     string `json:"result"`
}

// FileLogger writes audit entries as JSON lines to a file.
type FileLogger struct {
	mu     sync.Mutex
	writer io.WriteCloser
}

// NewFileLogger creates an audit logger that writes to the given file path.
// If path is empty, it writes to stdout.
func NewFileLogger(path string) (*FileLogger, error) {
	var w io.WriteCloser
	if path == "" {
		w = os.Stdout
	} else {
		f, err := os.OpenFile(path, os.O_CREATE|os.O_APPEND|os.O_WRONLY, 0644)
		if err != nil {
			return nil, fmt.Errorf("open audit log: %w", err)
		}
		w = f
	}
	return &FileLogger{writer: w}, nil
}

// Log writes an audit entry as a JSON line.
func (l *FileLogger) Log(entry Entry) error {
	if entry.Timestamp == "" {
		entry.Timestamp = time.Now().UTC().Format(time.RFC3339Nano)
	}

	data, err := json.Marshal(entry)
	if err != nil {
		return fmt.Errorf("marshal audit entry: %w", err)
	}

	l.mu.Lock()
	defer l.mu.Unlock()

	if _, err := l.writer.Write(append(data, '\n')); err != nil {
		return fmt.Errorf("write audit entry: %w", err)
	}
	return nil
}

// Close closes the underlying writer.
func (l *FileLogger) Close() error {
	l.mu.Lock()
	defer l.mu.Unlock()
	if l.writer != os.Stdout {
		return l.writer.Close()
	}
	return nil
}

# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] — 2026-03-28

### Added
- **Cross-platform builds:** Makefile targets for Linux (amd64/arm64/armv7), macOS (amd64/arm64), Windows (amd64/arm64)
- **Release packaging:** `make release-binaries` produces `.tar.gz` (Linux/macOS) and `.zip` (Windows) archives
- **GitHub Release:** `gh release create` command documented for CI/CD integration
- **README:** Comprehensive API documentation covering all packages (core, protocol, transport, security, services)
- **Replay tracker:** `Reset()` method to clear all tracked sequence state
- **Shared memory transport:** `runtime.Gosched()` yield in receive loop to prevent CPU spin

### Fixed
- **Duplicate symbol compilation error:** Removed `security/replay/tracker_fix.go` which duplicated `Tracker`, `ErrReplay`, and `defaultWindowSize` from `tracker.go`, causing build failures
- **SHM ring buffer capacity check:** Write method used 4-byte overhead check (`slotSize-4`) but only wrote a 2-byte length prefix; corrected to `slotSize-2`
- **SHM receive busy-loop:** `Connection.Receive()` busy-looped without yielding, burning 100% CPU; added `runtime.Gosched()` to yield to the scheduler
- **Server signal handling:** Replaced `syscall.SIGINT, syscall.SIGTERM` with portable `os.Interrupt` for Windows compatibility
- **ServerEndpoint unused field:** Renamed unused `mu sync.Mutex` to `sendMu` for future send serialization

### Changed
- **Makefile:** Complete rewrite with cross-compilation, release packaging, `fmt`, `vet`, and `lint` targets
- **go.mod:** Module path `github.com/embeddedos-org/eipc`, Go 1.22+
- **README:** Replaced placeholder README with full API reference, architecture diagram, quick start, wire protocol docs, and platform matrix

---

## [0.1.0] — 2026-03-27

### Added
- **Core:** Message types, endpoint API (client/server), priority-lane router with batch dispatch
- **Protocol:** Frame encoding/decoding, HMAC integrity, codec abstraction
- **Security:** Authentication (session tokens), capability-based authorization, HMAC integrity verification, replay detection (sliding window)
- **Transports:** TCP transport with length-prefixed framing, Unix domain socket transport, Windows named pipe transport
- **Services:** Service registry and discovery, message broker, policy engine, audit logging, health monitoring
- **CLI:** `eipc-server` and `eipc-client` demo binaries
- **C SDK:** Frame codec, HMAC, transport, JSON helpers under `sdk/c/`
- **Tests:** Unit tests for protocol, security, and services; integration test for end-to-end flow
- **Project infrastructure:** LICENSE (Apache 2.0), CONTRIBUTING.md, Makefile, Doxyfile

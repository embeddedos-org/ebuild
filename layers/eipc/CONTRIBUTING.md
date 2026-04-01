# Contributing to EIPC

Thank you for your interest in contributing to the IPC Protocol!

## Prerequisites

| Requirement | Version | Purpose |
|---|---|---|
| Go | 1.21+ | Core EIPC build and tests |
| CMake | 3.15+ | C SDK build |
| C compiler | C11 | C SDK (gcc, clang, or MSVC) |

## Getting Started

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/my-feature`
3. Make your changes
4. Run the build and tests locally
5. Submit a pull request

## Development Setup

### Go SDK

```bash
git clone https://github.com/embeddedos-org/eipc.git
cd eipc
go build ./...
go test -race -v ./...
```

### C SDK

```bash
cd sdk/c
mkdir build && cd build
cmake ..
cmake --build .
ctest --output-on-failure
```

## CI Requirements

All pull requests must pass the following CI checks before merging:

### Required Status Checks

| Check | Platform | What It Validates |
|---|---|---|
| **Build (ubuntu-latest)** | Linux | `go build`, `go test -race`, `go vet` |
| **Build (windows-latest)** | Windows | Cross-platform portability |
| **Build (macos-latest)** | macOS | Apple platform support |

### How to Verify Locally

Before submitting a PR, ensure all checks pass:

```bash
# Go SDK
go build ./...
go test -race -v ./...
go vet ./...
gofmt -l .

# C SDK
cd sdk/c && mkdir -p build && cd build
cmake ..
cmake --build .
ctest --output-on-failure
```

### Nightly Regression (Informational)

The nightly workflow runs additional checks not required for PRs but monitored for regressions:

- Full test suite with race detector on all 3 OS platforms
- Fuzz testing for protocol codec and security components

## Code Guidelines

### Go Style

- Follow the standard [Go Code Review Comments](https://github.com/golang/go/wiki/CodeReviewComments)
- Use `gofmt` for formatting
- Use `go vet` for static analysis
- Export only what is needed; keep internal APIs unexported
- Use meaningful package names (`transport`, `security`, `core`)
- Error messages should start with lowercase and not end with punctuation

### C Style (C SDK)

- Target **C11** standard
- Use **snake_case** for all identifiers: functions, variables, types
- Prefix all public symbols with `eipc_` (e.g., `eipc_frame_encode`, `eipc_transport_send`)
- Use `stdint.h` fixed-width types (`uint8_t`, `uint32_t`)
- No dynamic memory allocation in transport-critical paths
- Every public function must have a documentation comment

### Build Tags

- Use `//go:build !windows` for Unix-only code
- Use `//go:build windows` for Windows-only code

### Adding a Transport

1. Create a new directory under `transport/` (e.g., `transport/quic/`)
2. Implement the `Transport` interface: `Listen()`, `Dial()`, `Accept()`, `Close()`
3. Add build tags if the transport is platform-specific
4. Register the transport in `transport/registry.go`
5. Add unit tests and integration tests
6. Update `README.md` with transport documentation

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add Unix domain socket transport
fix: replay tracker window overflow
docs: add transport integration guide
ci: add fuzz testing to nightly
chore: bump go version to 1.22
```

### Pull Request Checklist

- [ ] `go build ./...` succeeds
- [ ] `go test -race ./...` passes
- [ ] `go vet ./...` clean
- [ ] `gofmt` applied
- [ ] C SDK builds and tests pass (if C code changed)
- [ ] New features include unit tests
- [ ] Platform-specific code uses build tags
- [ ] Commit messages follow conventional commits format

## Reporting Issues

- Use GitHub Issues with the appropriate label (`bug`, `enhancement`, `question`)
- Include: OS, Go version, and full error output
- For test failures: attach the full test log

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

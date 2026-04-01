# ADR-001: EoSuite Deployment Architecture

**Status:** Accepted  
**Date:** 2026-03-27  
**Author:** EoS Platform Team  

---

## Context

The EoS (Embedded Operating System) platform consists of 9 repositories that form a complete embedded ecosystem — from bootloader to AI inference. The platform needed:

1. An AI assistant (Ebot) for embedded developers
2. A client-server architecture that works on both host machines and EoS devices
3. A deployment path to compile, install, and test the client inside EoS simulation
4. CI/CD that validates the entire stack on every change

## Decision

### Architecture: Decoupled Client-Server with EoS-SDK Integration

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Host / Developer Machine                    │
│                                                                     │
│  ┌──────────────────────────────────────┐                           │
│  │        EoSuite (Ebot Client)         │                           │
│  │        github.com/embeddedos-org/    │                           │
│  │        EoSuite                       │                           │
│  │                                      │                           │
│  │  ┌──────────────────────────────┐    │                           │
│  │  │ ebot CLI                     │    │    ┌───────────────────┐  │
│  │  │  • ebot chat "message"       │    │    │ cmake + EoS-SDK   │  │
│  │  │  • ebot ask "question"       │────┤    │ FetchContent      │  │
│  │  │  • ebot interactive          │    │    │ auto-downloads    │  │
│  │  │  • ebot suggest              │    │    │ eos-sdk from      │  │
│  │  │  • ebot status/tools/models  │    │    │ GitHub            │  │
│  │  └──────────────────────────────┘    │    └───────────────────┘  │
│  │                                      │                           │
│  │  ┌──────────────────────────────┐    │                           │
│  │  │ ebot_client library (C)      │    │                           │
│  │  │  • HTTP/JSON client          │    │                           │
│  │  │  • Conversation management   │    │                           │
│  │  │  • 15 built-in suggestions   │    │                           │
│  │  │  • Linked with eos_sdk       │    │                           │
│  │  └──────────────────────────────┘    │                           │
│  └──────────────────┬───────────────────┘                           │
│                     │ HTTP POST/GET                                  │
│                     │ 192.168.1.100:8420                             │
└─────────────────────┼───────────────────────────────────────────────┘
                      │
          ┌───────────▼───────────────────────────────────────────────┐
          │              EoS Device (192.168.1.100)                    │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐   │
          │  │              EAI (Ebot Server)                       │   │
          │  │              github.com/embeddedos-org/eai           │   │
          │  │                                                      │   │
          │  │  ┌────────────────────────────────────────────────┐  │   │
          │  │  │  HTTP Server (ebot/server.c)                   │  │   │
          │  │  │  Listening on 192.168.1.100:8420               │  │   │
          │  │  │                                                 │  │   │
          │  │  │  Endpoints:                                     │  │   │
          │  │  │    POST /v1/chat     → agent loop + LLM         │  │   │
          │  │  │    POST /v1/complete → direct inference          │  │   │
          │  │  │    GET  /v1/status   → server stats              │  │   │
          │  │  │    GET  /v1/tools    → tool registry              │  │   │
          │  │  │    GET  /v1/models   → available models           │  │   │
          │  │  │    POST /v1/reset    → clear conversation         │  │   │
          │  │  └───────────────┬─────────────────────────────────┘  │   │
          │  │                  │                                     │   │
          │  │  ┌───────────────▼─────────────────────────────────┐  │   │
          │  │  │  Agent Loop (min/src/agent.c)                   │  │   │
          │  │  │    think → act → observe                         │  │   │
          │  │  │    CALL:tool_name(key=val) parsing               │  │   │
          │  │  │    Conversation memory (last_context)             │  │   │
          │  │  └───────────────┬─────────────────────────────────┘  │   │
          │  │                  │                                     │   │
          │  │  ┌───────────────▼─────────────────────────────────┐  │   │
          │  │  │  LLM Runtime (min/src/runtime_llama.c)          │  │   │
          │  │  │    llama.cpp backend                              │  │   │
          │  │  │    Default model: phi-mini-q4 (2GB RAM)           │  │   │
          │  │  │    2048 context, 4 threads, greedy sampling       │  │   │
          │  │  └───────────────┬─────────────────────────────────┘  │   │
          │  │                  │                                     │   │
          │  │  ┌───────────────▼─────────────────────────────────┐  │   │
          │  │  │  Tool Registry                                   │  │   │
          │  │  │    mqtt.publish, device.read_sensor, http.get     │  │   │
          │  │  └───────────────┬─────────────────────────────────┘  │   │
          │  │                  │                                     │   │
          │  │  ┌───────────────▼─────────────────────────────────┐  │   │
          │  │  │  ENI Bridge (EIPC)                               │  │   │
          │  │  │    Neural intent → agent goal                     │  │   │
          │  │  │    TCP + HMAC authentication                      │  │   │
          │  │  └─────────────────────────────────────────────────┘  │   │
          │  └─────────────────────────────────────────────────────┘   │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐   │
          │  │  EoS Kernel + HAL + Services                         │   │
          │  │    33 HAL peripherals, RTOS kernel, OTA, crypto      │   │
          │  └─────────────────────────────────────────────────────┘   │
          │                                                            │
          │  ┌─────────────────────────────────────────────────────┐   │
          │  │  eBoot (Bootloader)                                  │   │
          │  │    24 board ports, secure boot, A/B slots             │   │
          │  └─────────────────────────────────────────────────────┘   │
          └────────────────────────────────────────────────────────────┘
```

## EoSuite Build & Deployment Flow

### 1. Host Build (Development)

```bash
# Clone and build on developer machine
git clone https://github.com/embeddedos-org/EoSuite.git
cd EoSuite

# Build with EoS-SDK (auto-fetched via FetchContent)
cmake -B build -DEOSUITE_FETCH_SDK=ON
cmake --build build

# Run locally — connects to EoS device at 192.168.1.100:8420
./build/ebot chat "How to configure PWM?"
./build/ebot interactive
```

### 2. Cross-Compilation (for EoS Target)

```bash
# Cross-compile for ARM64 EoS device
cmake -B build -G Ninja \
  -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc \
  -DCMAKE_SYSTEM_NAME=Linux \
  -DEOSUITE_FETCH_SDK=ON
cmake --build build
# Result: build/ebot (ARM64 binary)
```

### 3. Rootfs Deployment (EoS Image)

```bash
# Install ebot into EoS rootfs
cmake -B build \
  -DEOSUITE_INSTALL_ROOTFS=ON \
  -DEOSUITE_ROOTFS_DIR=/path/to/eos/rootfs
cmake --build build
cmake --install build
# Result: /path/to/eos/rootfs/usr/bin/ebot
```

### 4. QEMU Simulation Testing

```
cmake build → ebot binary → install to rootfs → QEMU boot → 5 tests:
  [TEST 1] ebot binary exists at /usr/bin/ebot
  [TEST 2] ebot version prints correctly
  [TEST 3] ebot help shows chat command
  [TEST 4] ebot suggest shows GPIO prompt
  [TEST 5] ebot status handles no-server gracefully
```

## Network Configuration

| Setting | Default | Description |
|---------|---------|-------------|
| Server Host | `192.168.1.100` | EoS device IP on local network |
| Server Port | `8420` | Ebot server port |
| Bind Address | `192.168.1.100` | Server binds to EoS device IP |

### Override at Runtime

```bash
# Connect to different server
ebot --host 10.0.0.50 --port 9000 chat "hello"

# Local development (loopback)
ebot --host 127.0.0.1 chat "hello"
```

### Override in Code

```c
ebot_client_t c;
ebot_client_init(&c, "10.0.0.50", 9000);
```

## CI/CD Architecture

### Per-Repo CI (on every push)

```
Push to any repo
    ↓
┌─────────────────────────────┐
│ Repo CI (Linux/Win/Mac)     │
│ + QEMU Sanity (13 jobs)     │
│   x86_64, ARM64, ARM32×5,   │
│   RISC-V×2, MIPS, PowerPC   │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ Cross-Repo Dispatch         │
│ (repository_dispatch)       │
└──────────────┬──────────────┘
               ↓
┌─────────────────────────────┐
│ eos-sdk Integration Suite   │
│ (9 jobs, all 8 repos)       │
│ + EoSuite deployed to       │
│   QEMU rootfs and tested    │
└─────────────────────────────┘
```

### Cross-Repo Dispatch Map

```
eos    → eboot, eai, eni, eos-sdk
eboot  → eos-sdk
eipc   → eai, eni, eos-sdk
eai    → eos-sdk
eni    → eos-sdk
ebuild → ALL 6 repos
```

### Integration Test Suite (eos-sdk)

| Job | Repos Validated |
|-----|----------------|
| Build All (native) | eos, eboot, eai, eni, eipc, eos-sdk, ebuild, EoSuite |
| Header Compatibility | Cross-repo #include chains |
| Version Consistency | CMake vs build.yaml, LICENSE, README, CHANGELOG |
| Cross-Compile aarch64 | eos, eboot, eai, eni, EoSuite |
| Cross-Compile arm | eos, eboot, eai, eni, EoSuite |
| Cross-Compile riscv64 | eos, eboot, eai, eni, EoSuite |
| QEMU Boot | Real x86_64 kernel + initramfs |
| EoSuite in EoS Sim | ebot binary deployed and tested inside QEMU |

### EoSuite QEMU Pipeline

| Job | What It Does |
|-----|-------------|
| Build + Test (native) | cmake + EoS-SDK + 11 unit tests |
| QEMU EoS Simulation | Compile ebot → install to rootfs → boot QEMU → run 5 tests inside EoS |
| QEMU ARM/RISC-V/MIPS | Verify QEMU binaries for 4 architectures |
| Sanity Gate | Enforce build pass |

## Component Responsibilities

| Component | Repo | Language | Role |
|-----------|------|----------|------|
| **EoSuite** | `EoSuite` | C | Ebot CLI client, chat window, suggestions |
| **ebot_client** | `EoSuite` | C | HTTP client library (libsbot_client.a) |
| **Ebot Server** | `eai/ebot` | C | HTTP/JSON AI server (libebot_server.a) |
| **Agent Loop** | `eai/min` | C | think→act→observe with tool calling |
| **LLM Runtime** | `eai/min` | C | llama.cpp (phi-mini-q4, 2GB RAM) |
| **Tool Registry** | `eai/common` | C | mqtt.publish, device.read_sensor, http.get |
| **ENI Bridge** | `eai/common` | C | Neural intent → agent goal via EIPC |
| **EoS-SDK** | `eos-sdk` | C | Unified SDK header, feature flags |
| **EoS** | `eos` | C | HAL, kernel, 41 profiles, 33 peripherals |
| **eBoot** | `eboot` | C | Bootloader, 24 boards, secure boot |
| **EIPC** | `eipc` | Go+C | IPC, security, transports |
| **ENI** | `eni` | C | Neural interface adapter |
| **eBuild** | `ebuild` | Python | Build system, 10 backends |

## Test Coverage

| Test Type | Count | Where |
|-----------|-------|-------|
| Ebot Server unit tests | 12 | eai/ebot/test_ebot_server.c |
| Ebot Client unit tests | 11 | EoSuite/tests/test_ebot_client.c |
| EoS Simulation tests | 5 | EoSuite QEMU workflow |
| ebuild tests | 156 | ebuild/tests/ |
| eos test suites | 8 | eos/tests/ |
| eboot test suites | 7 | eboot/tests/ |
| eipc Go tests | full | eipc/core, security, transport, services |
| QEMU board types | 11 | Per-repo QEMU workflow |
| Cross-compile archs | 3 | ARM, ARM64, RISC-V |
| Integration jobs | 9 | eos-sdk integration.yml |
| **Total CI jobs per trigger** | **104** | All repos combined |

## Consequences

### Positive

- **Decoupled** — client and server fail independently
- **Portable** — EoSuite compiles on host or cross-compiles for EoS target
- **Testable** — ebot binary runs inside QEMU EoS simulation on every CI run
- **Scalable** — EAI server can serve multiple clients or devices
- **Swappable** — LLM backend can change without touching client
- **API-driven** — HTTP/JSON interface, OpenAI-compatible response format

### Trade-offs

- HTTP overhead vs raw IPC (acceptable for AI inference latency)
- QEMU simulation != real hardware (but validates binary deployment path)
- phi-mini-q4 is basic (greedy sampling, 256 max tokens) — sufficient for embedded assistant

### Future Enhancements

- Streaming responses via chunked transfer encoding
- WebSocket support for real-time chat
- Chat template support (system/user/assistant roles)
- Temperature/top-k/top-p sampling controls
- ONNX/TFLite runtime backends (currently stubbed)
- Cloud fallback routing (currently stubbed)
- Multiple concurrent sessions

## References

- [EoS Platform Website](https://embeddedos-org.github.io)
- [EoSuite Repository](https://github.com/embeddedos-org/EoSuite)
- [EAI Repository](https://github.com/embeddedos-org/eai)
- [EoS-SDK Repository](https://github.com/embeddedos-org/eos-sdk)
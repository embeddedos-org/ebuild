# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.1.0] — 2026-03-27

### Added
- **EAI-Min:** Lightweight AI runtime with agent loop (think→call→done), router (local/cloud/auto), memory-lite KV store
- **EAI-Framework:** Industrial AI platform with runtime manager, orchestrator, policy engine, memory (namespaced KV with TTL), observability, and connector manager
- **Common contracts:** Config system, tool registry, security permissions, model manifest, runtime contract
- **Connectors:** MQTT, OPC-UA, Modbus, CAN bus industrial protocol connectors
- **Platform adapters:** Linux, Windows, EoS, and container platform implementations
- **Profiles:** Smart camera, industrial gateway, robot controller, mobile edge
- **CLI:** Command-line interface for EAI management
- **CI/CD:** GitHub Actions workflows for CI, nightly regression, and release automation
- **Project infrastructure:** LICENSE, CONTRIBUTING.md, build.yaml, Doxyfile
- **runtime_llama.h:** Public header for llama.cpp runtime integration (`min/include/eai_min/`)
- **MQTT connector:** Industrial MQTT publish/subscribe connector
- **OPC-UA connector:** OPC Unified Architecture client connector
- **CAN bus connector:** Controller Area Network connector for automotive/industrial
- **Modbus connector:** Modbus TCP/RTU connector for industrial automation

### Fixed
- **config.c:** Fixed dangling pointers in configuration teardown — all `config_*` fields are now nulled after `free()`
- **platform_eos.c:** EoS platform adapter — corrected initialization sequence and lifecycle hooks

### Changed
- Removed duplicate CMake targets and dead code from build system
- Cleaned up unused function prototypes and stale `#include` directives
- **runtime_llama.h:** Public header for llama.cpp runtime integration (`min/include/eai_min/`)
- **MQTT connector:** Industrial MQTT publish/subscribe connector
- **OPC-UA connector:** OPC Unified Architecture client connector
- **CAN bus connector:** Controller Area Network connector for automotive/industrial
- **Modbus connector:** Modbus TCP/RTU connector for industrial automation

### Fixed
- **config.c:** Fixed dangling pointers in configuration teardown — all `config_*` fields are now nulled after `free()`
- **platform_eos.c:** EoS platform adapter — corrected initialization sequence and lifecycle hooks

### Changed
- Removed duplicate CMake targets and dead code from build system
- Cleaned up unused function prototypes and stale `#include` directives

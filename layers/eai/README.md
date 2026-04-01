# EAI — Embedded AI Layer

**AI inference and agent framework for the EoS embedded OS platform.**

EAI provides on-device LLM inference, agent orchestration, and tool execution — from MCUs to edge servers. Supports Neuralink intents via ENI/EIPC bridge.

## Configurations

| Config | Option | Description |
|---|---|---|
| **Minimal** | `EAI_BUILD_MIN=ON` | Lightweight runtime for resource-constrained devices. llama.cpp backend, simple agent loop, memory-lite context. For RPi3/4, i.MX8M, MCUs with external RAM. |
| **Framework** | `EAI_BUILD_FRAMEWORK=ON` | Full industrial AI platform with runtime manager, connector bus, orchestrator, observability. For edge servers, Jetson, x86. |

Both configurations share the common library (tools, security, config, EIPC listener, logging).

## LLM Models for EoS

EAI includes a curated registry of **12 embedded-optimized LLM models** across 5 hardware tiers:

| Tier | RAM | Model | Params | Hardware | Use Case |
|---|---|---|---|---|---|
| **Micro** | < 100MB | TinyLlama 1.1B Q2_K | 1.1B | STM32H7, ESP32-S3 | Command parsing, simple Q&A |
| **Tiny** | 100-500MB | SmolLM 360M Q5 | 360M | RPi3, nRF5340 | Fast command routing |
| | | Qwen2 0.5B Q4 | 500M | RPi3, AM64x | Multilingual, tool calling |
| | | Phi-1.5 Q4 | 1.3B | RPi3, BeagleBone | Reasoning, code generation |
| **Small** | 500MB-2GB | Qwen2 1.5B Q4 | 1.5B | RPi4 (4GB), SiFive | Tool calling, function routing |
| | | Gemma 2B Q4 | 2B | RPi4 (8GB), Jetson Nano | Instruction following |
| | | Phi-2 Q4 | 2.7B | RPi4, i.MX8M | Reasoning, code, math |
| | | **Phi-3-mini Q4** (default) | 3.8B | RPi4 (8GB), i.MX8M+ | **EoS default** — general assistant |
| **Medium** | 2-4GB | Llama 3.2 3B Q4 | 3B | RPi5, Jetson Nano | State-of-art small, tool use |
| | | Mistral 7B Q3_K | 7B | Jetson Nano, x86 | General assistant |
| **Large** | 4GB+ | Llama 3.2 8B Q4 | 8B | x86 edge, Jetson Orin | Full-capability assistant |
| | | Qwen2.5 7B Q4 | 7B | x86 edge, Jetson Orin | Best multilingual + coding |

### Auto-select model for your hardware

```c
#include "models.h"

// Find best model that fits in 2GB RAM, 1GB storage
const eai_model_info_t *model = eai_model_find_best_fit(2048, 1024);
// → returns "phi-2-q4" (2.7B params, 600MB RAM, 500MB storage)

// Or select by tier
const eai_model_info_t *tiny = eai_model_find_by_tier(EAI_MODEL_TIER_TINY);
// → returns "phi-1.5-q4"

// Or by name
const eai_model_info_t *m = eai_model_find("llama-3.2-3b-q4");
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      EAI v0.1.0                              │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐   │
│  │              Model Registry (12 models)                │   │
│  │  micro: TinyLlama   tiny: SmolLM, Qwen2, Phi-1.5     │   │
│  │  small: Phi-2, Gemma, Phi-mini, Qwen2-1.5B           │   │
│  │  medium: Llama-3.2-3B, Mistral-7B                     │   │
│  │  large: Llama-3.2-8B, Qwen2.5-7B                     │   │
│  └──────────────────────┬────────────────────────────────┘   │
│                         │                                     │
│  ┌──────────────┐  ┌───▼──────────┐  ┌──────────────────┐   │
│  │  EAI-Min     │  │   Common     │  │  EAI-Framework   │   │
│  │  (lightweight)│  │              │  │  (full platform) │   │
│  │  agent loop  │  │  tools       │  │  runtime manager │   │
│  │  llama.cpp   │  │  security    │  │  connector bus   │   │
│  │  memory-lite │  │  config      │  │  orchestrator    │   │
│  │  router      │  │  EIPC listen │  │  observability   │   │
│  └──────────────┘  │  logging     │  └──────────────────┘   │
│                    └──────────────┘                           │
│                         │                                     │
│  ┌──────────────────────▼────────────────────────────────┐   │
│  │              Ebot Server (HTTP/JSON)                    │   │
│  │         192.168.1.100:8420                              │   │
│  │  /v1/chat  /v1/tools  /v1/models  /v1/status          │   │
│  └──────────────────────┬────────────────────────────────┘   │
│                         │                                     │
│  ┌──────────────────────▼────────────────────────────────┐   │
│  │              EIPC Bridge ← ENI Neural Intents          │   │
│  │         Neuralink → intent → agent → tool execution    │   │
│  └───────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Ebot Server

HTTP/JSON AI assistant server at `192.168.1.100:8420`:

| Endpoint | Method | Description |
|---|---|---|
| `/v1/chat` | POST | Chat with conversation history |
| `/v1/complete` | POST | Single-shot text completion |
| `/v1/tools` | GET | List available tools |
| `/v1/models` | GET | List available LLM models |
| `/v1/status` | GET | Server stats (requests, tokens) |
| `/v1/reset` | POST | Clear conversation history |

## Built-in Tools

| Tool | Description |
|---|---|
| `mqtt.publish` | Publish to MQTT broker |
| `device.read_sensor` | Read sensor value via HAL |
| `http.get` | HTTP GET request |
| `gpio.write` | Write GPIO pin |
| `system.info` | Get system information |

## Profiles

Pre-configured EAI profiles for common use cases:

| Profile | Model | Tools | Use Case |
|---|---|---|---|
| `robot-controller` | phi-mini-q4 | sensor, motor, mqtt | Robotic control |
| `smart-camera` | smollm-360m-q5 | http, mqtt | Vision inference |
| `industrial-gateway` | qwen2-1.5b-q4 | mqtt, sensor, gpio | Industrial IoT |
| `mobile-edge` | phi-1.5-q4 | http, system | Mobile edge AI |

## Build

```bash
# Full build (min + framework + models)
cmake -B build -DEAI_BUILD_TESTS=ON
cmake --build build

# Minimal only (lightweight, for SBCs)
cmake -B build -DEAI_BUILD_MIN=ON -DEAI_BUILD_FRAMEWORK=OFF

# With EIPC (receive ENI Neuralink intents)
cmake -B build -DEAI_EIPC_ENABLED=ON

# With real llama.cpp backend
cmake -B build -DEAI_LLAMA_CPP=ON
```

## License

MIT
# EAI Code Structure Guide

> Developer reference for the AI Layer codebase — how every module works, connects, and extends.

---

## Table of Contents

1. [Project Layout](#project-layout)
2. [Build System](#build-system)
3. [Common Layer](#common-layer)
4. [EAI-Min](#eai-min)
5. [EAI-Framework](#eai-framework)
6. [Platform Adapters](#platform-adapters)
7. [CLI](#cli)
8. [Profiles](#profiles)
9. [Data Flow Diagrams](#data-flow-diagrams)
10. [Extension Guide](#extension-guide)

---

## Project Layout

```
EAI/
├── CMakeLists.txt                 # Root build — orchestrates all subdirectories
├── .gitignore
├── README.md                      # Architecture overview & design philosophy
├── CODE_STRUCTURE.md              # This file — code-level documentation
│
├── common/                        # Shared contracts, types, tools (used by ALL)
│   ├── CMakeLists.txt             # Builds → libeai_common.a
│   ├── include/eai/
│   │   ├── common.h               # Master include (pulls in all headers)
│   │   ├── types.h                # Core types: eai_status_t, eai_kv_t, eai_buffer_t
│   │   ├── config.h               # Configuration system + profile loading
│   │   ├── log.h                  # Logging macros: EAI_LOG_INFO(), etc.
│   │   ├── manifest.h             # Model manifest: name, kind, runtime, footprint
│   │   ├── runtime_contract.h     # Runtime abstraction: ops vtable + inference I/O
│   │   ├── tool.h                 # Tool interface: registry, params, exec
│   │   ├── tools_builtin.h        # Built-in tool registration
│   │   └── security.h             # Permission model: grant, check, wildcards
│   └── src/
│       ├── config.c               # Config init, file parsing, profile loading
│       ├── log.c                  # Colored stderr logging with timestamps
│       ├── manifest.c             # Model manifest file parser + validator
│       ├── runtime_contract.c     # Runtime init/load/infer/unload + eai_status_str()
│       ├── tool_registry.c        # Tool registration, lookup, execution
│       ├── tools_builtin.c        # mqtt.publish, device.read_sensor, http.get
│       └── security.c             # Permission grant/check with wildcard support
│
├── min/                           # EAI-Min: lightweight IoT agent runtime
│   ├── CMakeLists.txt             # Builds → libeai_min.a (links eai_common)
│   ├── include/eai_min/
│   │   ├── eai_min.h              # Master include for EAI-Min
│   │   ├── runtime.h              # Min runtime wrapper + stub backend
│   │   ├── agent.h                # Single-agent loop with tool calling
│   │   ├── router.h               # Local/cloud/auto inference routing
│   │   └── memory_lite.h          # KV memory with LRU eviction
│   └── src/
│       ├── runtime.c              # Stub backend + runtime lifecycle
│       ├── agent.c                # Think → ToolCall → Done agent loop
│       ├── router.c               # Input-size-based routing decisions
│       └── memory_lite.c          # 128-entry KV store with persistence
│
├── framework/                     # EAI-Framework: industrial IoT platform
│   ├── CMakeLists.txt             # Builds → libeai_framework.a (links eai_common)
│   ├── include/eai_fw/
│   │   ├── eai_framework.h        # Master include for EAI-Framework
│   │   ├── runtime_manager.h      # Multi-runtime management (up to 8)
│   │   ├── orchestrator.h         # Workflow engine with step types
│   │   ├── connector.h            # Connector interface + manager
│   │   ├── memory.h               # Namespaced memory with TTL + GC
│   │   ├── policy.h               # Policy engine: ALLOW/DENY/AUDIT rules
│   │   └── observability.h        # Metrics (counter/gauge) + trace spans
│   └── src/
│       ├── runtime_manager.c      # Add/select/infer across multiple runtimes
│       ├── orchestrator.c         # Workflow runner: infer, tool, connector steps
│       ├── connector_mqtt.c       # MQTT connector (pub/sub/read)
│       ├── connector_opcua.c      # OPC-UA connector (node read/write)
│       ├── connector_modbus.c     # Modbus TCP (register read/write)
│       ├── connector_can.c        # CAN bus (8-byte frames) + connector manager
│       ├── memory.c               # Namespaced KV with TTL expiry and GC
│       ├── policy.c               # First-match rule evaluation
│       └── observability.c        # Metrics + microsecond trace spans
│
├── platform/                      # OS-specific adapters
│   ├── CMakeLists.txt             # Builds → libeai_platform.a
│   ├── include/eai/
│   │   └── platform.h             # Platform ops vtable interface
│   └── src/
│       ├── platform.c             # Auto-detection + init dispatch
│       ├── platform_linux.c       # sysfs GPIO, sysinfo, thermal zones
│       └── platform_windows.c     # GlobalMemoryStatusEx, OSVERSIONINFO
│
├── cli/                           # The `eai` command-line tool
│   ├── CMakeLists.txt             # Builds → eai executable
│   └── src/
│       └── main.c                 # CLI: run, serve, status, tools, profile
│
├── profiles/                      # Deployment configuration presets
│   ├── smart-camera/profile.yaml
│   ├── industrial-gateway/profile.yaml
│   ├── robot-controller/profile.yaml
│   └── mobile-edge/profile.yaml
│
└── tests/
    └── CMakeLists.txt             # Test harness placeholder
```

---

## Build System

The project uses **CMake** (minimum 3.16) targeting **C11**.

### Build Options

| Option                  | Default | Description                          |
|-------------------------|---------|--------------------------------------|
| `EAI_BUILD_MIN`         | ON      | Build EAI-Min lightweight runtime    |
| `EAI_BUILD_FRAMEWORK`   | ON      | Build EAI-Framework industrial stack |
| `EAI_BUILD_CLI`         | ON      | Build the `eai` CLI tool             |
| `EAI_BUILD_TESTS`       | OFF     | Build unit tests                     |
| `EAI_PLATFORM_LINUX`    | ON      | Enable Linux platform adapter        |
| `EAI_PLATFORM_WINDOWS`  | OFF     | Enable Windows platform adapter      |
| `EAI_PLATFORM_EOS`  | OFF     | Enable EoS platform adapter      |
| `EAI_PLATFORM_CONTAINER`| OFF     | Enable container platform adapter    |

### Library Dependency Graph

```
eai (executable)
 ├── eai_common    (static lib)
 ├── eai_min       (static lib) ──→ eai_common
 ├── eai_framework (static lib) ──→ eai_common
 └── eai_platform  (static lib) ──→ eai_common
```

### Quick Build

```bash
mkdir build && cd build
cmake ..
cmake --build .
```

### Cross-compile for ARM64

```bash
cmake .. -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc \
         -DEAI_PLATFORM_LINUX=ON
cmake --build .
```

---

## Common Layer

**Library**: `libeai_common.a`
**Headers**: `common/include/eai/`

This is the foundation. Both EAI-Min and EAI-Framework depend on it. Every shared type, contract, and utility lives here.

### types.h — Core Types

Defines all fundamental types used across the project.

```c
eai_status_t    // Return codes: EAI_OK, EAI_ERR_NOMEM, EAI_ERR_IO, etc.
eai_variant_t   // EAI_VARIANT_MIN or EAI_VARIANT_FRAMEWORK
eai_mode_t      // EAI_MODE_LOCAL, EAI_MODE_CLOUD, EAI_MODE_HYBRID
eai_log_level_t // EAI_LOG_TRACE through EAI_LOG_FATAL
eai_kv_t        // Key-value pair { const char *key; const char *value; }
eai_buffer_t    // Generic byte buffer { uint8_t *data; size_t len, cap; }
```

**`eai_status_t`** is used as the return type for nearly every function. The function `eai_status_str()` in `runtime_contract.c` converts it to a human-readable string.

### config.h / config.c — Configuration System

Manages all EAI configuration — variant selection, runtime providers, tool lists, connector lists, and policy.

```c
eai_config_t cfg;
eai_config_init(&cfg);                               // defaults: min, local, no tools
eai_config_load_profile(&cfg, "industrial-gateway");  // load preset
eai_config_load_file(&cfg, "config.yaml");            // load from file
eai_config_dump(&cfg);                                // print to stdout
```

**Profile loading** is hardcoded in `config.c`. Each profile name maps to a specific configuration:

| Profile              | Variant   | Mode  | Runtimes              | Connectors         | Tools                                      |
|----------------------|-----------|-------|-----------------------|--------------------|---------------------------------------------|
| `smart-camera`       | framework | local | onnxruntime           | —                  | device.read_sensor, http.get                |
| `industrial-gateway` | framework | local | onnxruntime, llama.cpp| mqtt, opcua, modbus| mqtt.publish, device.read_sensor, http.get  |
| `robot-controller`   | framework | local | onnxruntime, tflite   | can, mqtt          | device.read_sensor, mqtt.publish            |
| `mobile-edge`        | min       | hybrid| llama.cpp             | —                  | http.get, device.read_sensor                |

### log.h / log.c — Logging

Color-coded, timestamped logging to stderr.

```c
EAI_LOG_INFO("my-module", "connected to %s:%d", host, port);
// Output: 14:32:01 [INFO] my-module: connected to localhost:1883

eai_log_set_level(EAI_LOG_DEBUG);   // show debug messages
eai_log_set_output(log_file);       // redirect to file
```

Each level has its own ANSI color: TRACE=gray, DEBUG=cyan, INFO=green, WARN=yellow, ERROR=red, FATAL=magenta.

### manifest.h / manifest.c — Model Manifest

Describes an AI model's metadata — what it is, what runtime it needs, how much memory it uses, what architectures it supports.

```c
eai_model_manifest_t m;
eai_manifest_load(&m, "models/phi-mini.manifest");   // parse from file
eai_manifest_validate(&m);                           // check required fields
eai_manifest_print(&m);                              // dump to stdout
```

Key fields in `eai_model_manifest_t`:

| Field         | Type                 | Description                          |
|---------------|----------------------|--------------------------------------|
| `name`        | `char[64]`           | Model name (e.g., "phi-mini-q4")     |
| `kind`        | `eai_model_kind_t`   | LLM, vision, anomaly, classification |
| `runtime`     | `eai_runtime_type_t` | llama.cpp, ONNX, TFLite, custom      |
| `version`     | `char[16]`           | Semantic version                     |
| `footprint`   | `{ram_mb, storage_mb}` | Memory requirements                |
| `compat_arch` | `eai_arch_t[]`       | ARM64, x86_64, RISCV64, ARM32       |
| `hash`        | `char[72]`           | Integrity hash (sha256:...)          |

### runtime_contract.h / runtime_contract.c — Runtime Abstraction

The core abstraction that allows swapping AI inference backends. Uses a **vtable pattern** (`eai_runtime_ops_t`) so backends can be plugged in without changing caller code.

```c
// The ops vtable — each backend implements these 5 functions:
typedef struct {
    const char *name;
    eai_status_t (*init)(eai_runtime_t *rt);
    eai_status_t (*load_model)(eai_runtime_t *rt, const eai_model_manifest_t *m, const char *path);
    eai_status_t (*infer)(eai_runtime_t *rt, const eai_inference_input_t *in, eai_inference_output_t *out);
    eai_status_t (*unload_model)(eai_runtime_t *rt);
    void         (*shutdown)(eai_runtime_t *rt);
} eai_runtime_ops_t;
```

Usage pattern:

```c
eai_runtime_t rt;
eai_runtime_init(&rt, &eai_runtime_stub_ops);   // plug in backend
eai_runtime_load(&rt, &manifest, "model.gguf");  // load model
eai_runtime_infer(&rt, &input, &output);          // run inference
eai_runtime_unload(&rt);                           // free model
eai_runtime_shutdown(&rt);                         // cleanup
```

**Inference I/O types**:

```
eai_inference_input_t:
  ├── text       (const char *)     — text prompt
  ├── text_len   (size_t)
  ├── binary     (const void *)     — image/audio data
  └── binary_len (size_t)

eai_inference_output_t:
  ├── text        (char[4096])      — generated response
  ├── text_len    (size_t)
  ├── confidence  (float)           — 0.0 to 1.0
  ├── tokens_used (uint32_t)
  └── latency_ms  (uint32_t)
```

### tool.h / tool_registry.c — Tool Interface

Tools are named functions with typed parameters that agents can call. Each tool has a parameter schema, required permissions, and an execution function.

```c
// Define a tool
eai_tool_t tool = {
    .name        = "mqtt.publish",
    .description = "Publish message to MQTT topic",
    .params      = {
        { "topic",   EAI_PARAM_STRING, true  },
        { "payload", EAI_PARAM_STRING, true  },
        { "qos",     EAI_PARAM_INT,    false },
    },
    .param_count      = 3,
    .permissions      = { "mqtt:write" },
    .permission_count = 1,
    .exec             = my_mqtt_publish_fn,
};

// Register and use
eai_tool_registry_t reg;
eai_tool_registry_init(&reg);
eai_tool_register(&reg, &tool);

eai_tool_t *t = eai_tool_find(&reg, "mqtt.publish");
eai_tool_result_t result;
eai_tool_exec(t, args, arg_count, &result);
```

The registry holds up to **64 tools** (`EAI_TOOL_REGISTRY_MAX`). Each tool can have up to **16 params** and **8 permissions**.

### tools_builtin.h / tools_builtin.c — Built-in Tools

Three tools ship with EAI:

| Tool                 | Required Params       | Optional  | Permission   | Description                    |
|----------------------|-----------------------|-----------|--------------|--------------------------------|
| `mqtt.publish`       | topic, payload        | qos       | mqtt:write   | Publish message to MQTT broker |
| `device.read_sensor` | sensor_id             | type      | sensor:read  | Read value from hardware sensor|
| `http.get`           | url                   | timeout   | network:http | Perform HTTP GET request       |

Register all at once:

```c
eai_tool_registry_t reg;
eai_tool_registry_init(&reg);
eai_tools_register_builtins(&reg);   // registers all 3
```

### security.h / security.c — Permission Model

Guards tool execution with a permission system. Supports exact match and **wildcard** patterns.

```c
eai_security_ctx_t ctx;
eai_security_ctx_init(&ctx, "agent-0");
eai_security_grant(&ctx, "sensor:*");       // wildcard: matches sensor:read, sensor:write
eai_security_grant(&ctx, "mqtt:write");

eai_security_check(&ctx, "sensor:read");    // true  (wildcard match)
eai_security_check(&ctx, "mqtt:write");     // true  (exact match)
eai_security_check(&ctx, "mqtt:admin");     // false (no match)

// Check all permissions required by a tool
const char *perms[] = { "sensor:read" };
eai_security_check_tool(&ctx, perms, 1);    // true
```

---

## EAI-Min

**Library**: `libeai_min.a`
**Headers**: `min/include/eai_min/`
**Depends on**: `libeai_common.a`

EAI-Min is the lightweight variant designed for edge nodes, smart sensors, and low-memory IoT devices. It runs a single agent with a single runtime backend.

### runtime.h / runtime.c — Min Runtime

Wraps the common `eai_runtime_t` with convenience settings (max tokens, temperature).

```c
eai_min_runtime_t rt;
eai_min_runtime_create(&rt, EAI_RUNTIME_LLAMA_CPP);       // select backend
eai_min_runtime_load(&rt, "model.gguf", &manifest);        // load model
eai_min_runtime_infer(&rt, "prompt text", buf, buf_size);  // text-in, text-out
eai_min_runtime_destroy(&rt);                               // cleanup
```

Currently ships with a **stub backend** (`eai_runtime_stub_ops`) that returns placeholder responses. To integrate a real backend (e.g., llama.cpp):

1. Implement the 5 functions in `eai_runtime_ops_t`
2. Assign to a new `const eai_runtime_ops_t` variable
3. Wire it into the `switch` in `eai_min_runtime_create()`

### agent.h / agent.c — Agent Loop

The core agent loop follows a **Think, Act, Observe** cycle:

```
┌──────────┐     ┌───────────┐     ┌──────────┐
│ THINKING │────→│ TOOL_CALL │────→│ THINKING │──→ ...
└──────────┘     └───────────┘     └──────────┘
      │                                  │
      └──── (no tool call) ─────────────→│
                                   ┌──────────┐
                                   │   DONE   │
                                   └──────────┘
```

**State machine**: `IDLE → THINKING → TOOL_CALL → THINKING → ... → DONE | ERROR`

```c
eai_min_agent_t agent;
eai_min_agent_init(&agent, &runtime, &tools, &memory);

eai_agent_task_t task = {
    .goal           = "Monitor sensors and report anomalies",
    .offline_only   = true,
    .max_iterations = 5,
};

eai_min_agent_run(&agent, &task);
printf("Result: %s\n", eai_min_agent_output(&agent));
eai_min_agent_reset(&agent);   // reuse for next task
```

**Tool calling protocol**: When the model output starts with `CALL:<tool_name>(<args>)`, the agent parses the tool name, looks it up in the registry, executes it, and feeds the result back as context for the next inference.

### router.h / router.c — Inference Router

Decides whether inference runs locally or in the cloud.

```c
eai_min_router_t router;
eai_min_router_init(&router, EAI_ROUTE_AUTO);
eai_min_router_set_cloud(&router, "https://api.example.com/infer", "key123");

eai_route_target_t target = eai_min_router_decide(&router, &input);
```

Three routing modes:

| Mode              | Behavior                                           |
|-------------------|----------------------------------------------------|
| `EAI_ROUTE_LOCAL` | Always local inference                             |
| `EAI_ROUTE_CLOUD` | Always cloud (falls back to local if unavailable)  |
| `EAI_ROUTE_AUTO`  | Large inputs (>2KB) go to cloud when available     |

### memory_lite.h / memory_lite.c — Lightweight Memory

A simple key-value store (128 entries max) that gives agents persistent context across tasks.

```c
eai_mem_lite_t mem;
eai_mem_lite_init(&mem, "/data/eai/memory.dat");

eai_mem_lite_set(&mem, "last_sensor", "temp=23.5C", false);   // volatile
eai_mem_lite_set(&mem, "device_id",   "GW-001",    true);     // persistent

const char *val = eai_mem_lite_get(&mem, "last_sensor");

eai_mem_lite_save(&mem);   // writes persistent entries to disk
eai_mem_lite_load(&mem);   // restores from disk
```

**Eviction**: When full, evicts the oldest non-persistent entry (LRU-style). Persistent entries survive eviction and disk save/load cycles.

---

## EAI-Framework

**Library**: `libeai_framework.a`
**Headers**: `framework/include/eai_fw/`
**Depends on**: `libeai_common.a`

EAI-Framework is the industrial-grade variant — designed for factory gateways, robotics controllers, and multi-sensor platforms. It supports multiple runtimes, protocol connectors, workflows, and observability.

### runtime_manager.h / runtime_manager.c — Multi-Runtime Manager

Manages up to **8 runtime backends** simultaneously (e.g., ONNX for vision + llama.cpp for LLM).

```c
eai_fw_runtime_manager_t mgr;
eai_fw_rtmgr_init(&mgr);

eai_fw_rtmgr_add(&mgr, &onnx_ops);       // index 0
eai_fw_rtmgr_add(&mgr, &llamacpp_ops);    // index 1

eai_fw_rtmgr_load_model(&mgr, 0, &vision_manifest, "model.onnx");
eai_fw_rtmgr_load_model(&mgr, 1, &llm_manifest,    "model.gguf");

eai_fw_rtmgr_infer(&mgr, 0,  &image_input, &output);  // vision inference
eai_fw_rtmgr_infer(&mgr, -1, &text_input,  &output);   // -1 = use active runtime
eai_fw_rtmgr_select(&mgr, 1);                           // switch active to llama.cpp

eai_fw_rtmgr_shutdown(&mgr);   // unloads all models and cleans up
```

### connector.h / connector_*.c — Protocol Connectors

Connectors abstract industrial protocols through a common ops vtable:

```c
typedef struct {
    const char *name;
    eai_connector_type_t type;
    eai_status_t (*connect)(conn, params, param_count);
    eai_status_t (*disconnect)(conn);
    eai_status_t (*read)(conn, address, buf, buf_size, bytes_read);
    eai_status_t (*write)(conn, address, data, data_len);
    eai_status_t (*subscribe)(conn, topic, callback);   // MQTT only
} eai_connector_ops_t;
```

**Four connectors ship**:

| Connector | Protocol    | Default Endpoint          | Key Features              |
|-----------|-------------|---------------------------|---------------------------|
| MQTT      | MQTT 3.1.1  | localhost:1883            | pub, sub, read, write     |
| OPC-UA    | OPC-UA      | opc.tcp://localhost:4840  | node read/write           |
| Modbus    | Modbus TCP  | localhost:502             | register read/write       |
| CAN       | CAN bus     | can0 @ 500kbps           | 8-byte frame read/write   |

**Connector Manager** (`eai_fw_connector_mgr_t`) holds up to 16 connectors:

```c
eai_fw_connector_mgr_t conn_mgr;
eai_fw_conn_mgr_init(&conn_mgr);
eai_fw_conn_add(&conn_mgr, "mqtt",   &eai_connector_mqtt_ops);
eai_fw_conn_add(&conn_mgr, "opcua",  &eai_connector_opcua_ops);
eai_fw_conn_add(&conn_mgr, "modbus", &eai_connector_modbus_ops);
eai_fw_conn_add(&conn_mgr, "can",    &eai_connector_can_ops);
eai_fw_conn_connect_all(&conn_mgr, params, param_count);

// Use a specific connector
eai_fw_connector_t *mqtt = eai_fw_conn_find(&conn_mgr, "mqtt");
mqtt->ops->write(mqtt, "sensors/temp", "{\"value\":23.5}", 15);

eai_fw_conn_disconnect_all(&conn_mgr);
```

Note: The connector manager implementation lives in `connector_can.c` alongside the CAN connector ops.

### orchestrator.h / orchestrator.c — Workflow Engine

Executes multi-step workflows that combine inference, tool calls, and connector I/O.

**Step types**:

| Step Type               | What It Does                                   |
|-------------------------|------------------------------------------------|
| `EAI_STEP_INFER`        | Run inference on the active runtime             |
| `EAI_STEP_TOOL_CALL`    | Execute a registered tool by name               |
| `EAI_STEP_CONNECTOR_READ`  | Read data from a named connector             |
| `EAI_STEP_CONNECTOR_WRITE` | Write data to a named connector              |
| `EAI_STEP_CONDITION`    | Branch (defaults to success path currently)     |
| `EAI_STEP_DELAY`        | Pause (no-op in sync mode)                     |

Each step has `next_on_success` and `next_on_failure` fields for flow control (use -1 for "next step"):

```c
eai_workflow_t wf = {
    .name       = "sensor-check",
    .step_count = 3,
    .steps = {
        { .type = EAI_STEP_CONNECTOR_READ,  .name = "read-temp",
          .target = "modbus", .next_on_success = -1, .next_on_failure = -1 },
        { .type = EAI_STEP_INFER,           .name = "analyze",
          .target = "llm",    .next_on_success = -1, .next_on_failure = -1 },
        { .type = EAI_STEP_TOOL_CALL,       .name = "publish-alert",
          .target = "mqtt.publish", .next_on_success = -1, .next_on_failure = -1 },
    },
};

eai_fw_orchestrator_t orch;
eai_fw_orch_init(&orch, &rt_mgr, &tools, &conn_mgr, &policy);
eai_fw_orch_load_workflow(&orch, &wf);
eai_fw_orch_run(&orch);       // runs all steps sequentially
eai_fw_orch_pause(&orch);     // pause mid-workflow
eai_fw_orch_resume(&orch);    // continue from paused step
eai_fw_orch_reset(&orch);     // clear workflow
```

**Policy integration**: Before each step executes, the orchestrator checks the policy engine. If the policy returns `EAI_POLICY_DENY`, the step is skipped with `EAI_ERR_PERMISSION`.

### memory.h / memory.c — Namespaced Memory

A larger key-value store (1024 entries) with **namespaces**, **TTL expiry**, and **garbage collection**.

```c
eai_fw_memory_t mem;
eai_fw_mem_init(&mem, "/data/eai/memory/");

eai_fw_mem_set(&mem, "sensors", "temp_1", "23.5", 300);    // expires in 5 min
eai_fw_mem_set(&mem, "config",  "threshold", "40.0", 0);    // never expires (persistent)

const char *val = eai_fw_mem_get(&mem, "sensors", "temp_1");  // NULL if expired

int cleaned = eai_fw_mem_gc(&mem);   // remove expired entries

eai_fw_mem_save(&mem);   // persist to /data/eai/memory/memory.dat
eai_fw_mem_load(&mem);   // restore from disk
```

**Differences from EAI-Min memory**:

| Feature        | memory_lite (Min)       | memory (Framework)           |
|----------------|-------------------------|------------------------------|
| Max entries    | 128                     | 1024                         |
| Key size       | 64 bytes                | 128 bytes                    |
| Value size     | 512 bytes               | 2048 bytes                   |
| Namespaces     | No                      | Yes (32-char namespace)      |
| TTL            | No                      | Yes (seconds, 0 = permanent) |
| GC             | LRU eviction only       | TTL-based garbage collection |

### policy.h / policy.c — Policy Engine

Controls what agents, tools, and connectors can do. Rules are evaluated **first-match** order.

```c
eai_fw_policy_t policy;
eai_fw_policy_init(&policy);

// Allow all tool execution
eai_policy_rule_t allow_tools = {
    .subject   = "orchestrator",
    .resource  = "*",
    .operation = "exec",
    .action    = EAI_POLICY_ALLOW,
};
eai_fw_policy_add_rule(&policy, &allow_tools);

// Deny dangerous connector writes
eai_policy_rule_t deny_can_write = {
    .subject   = "*",
    .resource  = "can",
    .operation = "write",
    .action    = EAI_POLICY_DENY,
};
eai_fw_policy_add_rule(&policy, &deny_can_write);

// Check a specific action
eai_policy_action_t act = eai_fw_policy_check(&policy, "orchestrator", "can", "write");
// → EAI_POLICY_DENY

eai_fw_policy_dump(&policy);   // print all rules
```

Three possible actions:

| Action             | Behavior                              |
|--------------------|---------------------------------------|
| `EAI_POLICY_ALLOW` | Permit the operation                  |
| `EAI_POLICY_DENY`  | Block the operation                   |
| `EAI_POLICY_AUDIT` | Permit but log the operation          |

Global policy settings: `cloud_fallback`, `allow_external_tools`, `max_inference_ms`, `max_memory_mb`.

### observability.h / observability.c — Metrics and Tracing

Provides counters, gauges, and trace spans for monitoring EAI operations.

```c
eai_fw_observability_t obs;
eai_fw_obs_init(&obs, true);   // enabled

// Metrics
eai_fw_obs_counter_inc(&obs, "eai.inferences", 1);
eai_fw_obs_counter_inc(&obs, "eai.tool_calls", 1);
eai_fw_obs_gauge_set(&obs, "eai.memory_used_mb", 256.0);

// Trace spans (microsecond precision)
eai_fw_obs_span_start(&obs, "inference", NULL);          // root span
eai_fw_obs_span_start(&obs, "tokenize", "inference");    // child span
eai_fw_obs_span_end(&obs, "tokenize");                    // record duration
eai_fw_obs_span_end(&obs, "inference");

eai_fw_obs_dump_metrics(&obs);   // print all metrics
eai_fw_obs_dump_spans(&obs);     // print all spans with durations
```

Supports up to **128 metrics** and **256 trace spans**. Uses platform-specific high-resolution timers (`QueryPerformanceCounter` on Windows, `gettimeofday` on Linux).

---

## Platform Adapters

**Library**: `libeai_platform.a`
**Headers**: `platform/include/eai/`

Platform adapters abstract OS-specific operations (device info, GPIO, memory stats, CPU temperature) behind a common vtable.

### platform.h — Interface

```c
typedef struct {
    const char *name;
    eai_status_t (*init)(eai_platform_t *plat);
    eai_status_t (*get_device_info)(plat, buf, buf_size);
    eai_status_t (*read_gpio)(plat, pin, *value);
    eai_status_t (*write_gpio)(plat, pin, value);
    eai_status_t (*get_memory_info)(plat, *total, *available);
    eai_status_t (*get_cpu_temp)(plat, *temp_c);
    void         (*shutdown)(plat);
} eai_platform_ops_t;
```

### Auto-Detection

```c
eai_platform_t plat;
eai_platform_detect(&plat);   // picks linux or windows based on #ifdef _WIN32
```

### Platform-Specific Implementations

| Operation       | Linux                                | Windows                    |
|-----------------|--------------------------------------|----------------------------|
| device_info     | Reads `/etc/os-release`              | `OSVERSIONINFO`            |
| read_gpio       | sysfs `/sys/class/gpio/gpioN/value`  | Unsupported                |
| write_gpio      | sysfs `/sys/class/gpio/gpioN/value`  | Unsupported                |
| memory_info     | `sysinfo()` struct                   | `GlobalMemoryStatusEx()`   |
| cpu_temp        | `/sys/class/thermal/thermal_zone0`   | Unsupported                |

Each platform file includes a stub definition for the opposite OS so the linker symbol always exists (e.g., `platform_linux.c` has a `_WIN32` stub).

---

## CLI

**Source**: `cli/src/main.c`
**Binary**: `eai` (or `eai.exe` on Windows)

The CLI is the main entry point for interacting with EAI. It links all four libraries.

### Commands

| Command               | Description                                        |
|-----------------------|----------------------------------------------------|
| `eai run`             | Start AI agent with default config (EAI-Min)       |
| `eai run --profile X` | Start with a named profile                         |
| `eai run --config F`  | Start with a config file                           |
| `eai serve`           | Start HTTP inference server (placeholder)          |
| `eai status`          | Show platform, device info, memory, version        |
| `eai tools`           | List all registered built-in tools                 |
| `eai profile <name>`  | Load and display a profile configuration           |
| `eai config <file>`   | Load and display a config file                     |
| `eai version`         | Show version, variants, tools, protocols           |
| `eai help`            | Show usage information                             |

### How `eai run` Works

```
1. Parse CLI flags (--profile, --config)
2. Load configuration (eai_config_t)
3. Register built-in tools
4. Check cfg.variant:
   ├── EAI_VARIANT_MIN:
   │   ├── Create eai_min_runtime_t (stub backend)
   │   ├── Load model from manifest
   │   ├── Create eai_mem_lite_t
   │   ├── Create eai_min_agent_t
   │   └── Run agent loop → print output
   └── EAI_VARIANT_FRAMEWORK:
       ├── Create eai_fw_runtime_manager_t + add stub
       ├── Create eai_fw_connector_mgr_t + add connectors from config
       ├── Connect all connectors
       ├── Create eai_fw_policy_t
       ├── Create eai_fw_observability_t
       ├── Create eai_fw_orchestrator_t
       └── Print initialization summary
```

---

## Profiles

**Location**: `profiles/<name>/profile.yaml`

Profiles are YAML files that define complete deployment configurations. They are also hardcoded as presets in `config.c`.

### Profile Structure

```yaml
ai:
  variant: framework           # min or framework
  mode: local                  # local, cloud, hybrid, local-first

  runtime:
    providers:                  # framework: list of runtimes
      - onnxruntime
      - llama.cpp
    provider: llama.cpp         # min: single runtime

  tools:                        # which built-in tools to enable
    - mqtt.publish
    - device.read_sensor
    - http.get

  connectors:                   # which protocol connectors (framework only)
    - mqtt
    - opcua
    - modbus

  policy:
    cloud_fallback: false
    max_inference_ms: 30000
    max_memory_mb: 2048

  observability: true

  hardware:                     # informational — not parsed by config.c yet
    accelerator: cpu
    can_bus: true
    gpio: true

  description: >
    Human-readable description of the deployment scenario.
```

---

## Data Flow Diagrams

### EAI-Min: Edge Agent Flow

```
┌────────────┐     ┌──────────┐     ┌──────────────┐
│   Config   │────→│ Runtime  │────→│  Agent Loop   │
│  (profile) │     │ (stub/   │     │               │
│            │     │  llama)  │     │ Think→Act→    │
└────────────┘     └──────────┘     │ Observe→Done  │
                                    └───────┬───────┘
                   ┌──────────┐             │
                   │  Memory  │←────────────┤ stores context
                   │  (lite)  │             │
                   └──────────┘             │
                   ┌──────────┐             │
                   │  Tools   │←────────────┘ calls tools
                   │ Registry │
                   └──────────┘
```

### EAI-Framework: Industrial Gateway Flow

```
┌────────────┐     ┌──────────────────────────────────────────┐
│   Config   │────→│             Orchestrator                  │
│  (profile) │     │                                          │
└────────────┘     │  ┌────────┐  ┌────────┐  ┌───────────┐  │
                   │  │ Infer  │→ │ Tool   │→ │ Connector │  │
                   │  │ Step   │  │ Step   │  │ Step      │  │
                   │  └────┬───┘  └────┬───┘  └─────┬─────┘  │
                   └───────┼──────────┼────────────┼──────────┘
                           │          │            │
                   ┌───────▼───┐ ┌────▼────┐ ┌────▼──────────┐
                   │ Runtime   │ │ Tool    │ │ Connectors    │
                   │ Manager   │ │ Registry│ │               │
                   │           │ │         │ │ ┌────┐ ┌────┐ │
                   │ [onnx]    │ │ [mqtt]  │ │ │MQTT│ │OPCUA││
                   │ [llama]   │ │ [sensor]│ │ │    │ │    │ │
                   │ [tflite]  │ │ [http]  │ │ └────┘ └────┘ │
                   └───────────┘ └─────────┘ │ ┌────┐ ┌────┐ │
                                             │ │Modb│ │CAN │ │
                   ┌───────────┐             │ │    │ │    │ │
                   │ Policy    │             │ └────┘ └────┘ │
                   │ Engine    │←── checks ──│               │
                   └───────────┘             └───────────────┘

                   ┌───────────┐   ┌───────────────┐
                   │ Memory    │   │ Observability  │
                   │ (ns+TTL)  │   │ metrics+spans  │
                   └───────────┘   └───────────────┘
```

### Cross-Component Type Flow

```
eai_config_t ──→ selects variant + mode + tools + connectors
     │
     ├──→ EAI-Min path:
     │    eai_min_runtime_t → eai_runtime_t → eai_runtime_ops_t (vtable)
     │    eai_min_agent_t   → uses runtime + tool_registry + memory_lite
     │
     └──→ EAI-Framework path:
          eai_fw_runtime_manager_t → multiple eai_runtime_t instances
          eai_fw_orchestrator_t    → uses rt_mgr + tools + connectors + policy
          eai_fw_connector_mgr_t  → multiple eai_fw_connector_t instances
          eai_fw_policy_t         → checked before each orchestrator step
          eai_fw_observability_t  → records metrics/spans during execution
```

---

## Extension Guide

### Adding a New Runtime Backend

1. Create `my_backend.c` (can live anywhere, e.g., `min/src/`)
2. Implement the ops vtable:

```c
static eai_status_t my_init(eai_runtime_t *rt) { ... }
static eai_status_t my_load(eai_runtime_t *rt, const eai_model_manifest_t *m, const char *p) { ... }
static eai_status_t my_infer(eai_runtime_t *rt, const eai_inference_input_t *in, eai_inference_output_t *out) { ... }
static eai_status_t my_unload(eai_runtime_t *rt) { ... }
static void my_shutdown(eai_runtime_t *rt) { ... }

const eai_runtime_ops_t my_backend_ops = {
    .name = "my-backend", .init = my_init, .load_model = my_load,
    .infer = my_infer, .unload_model = my_unload, .shutdown = my_shutdown,
};
```

3. Register it in `eai_min_runtime_create()` or `eai_fw_rtmgr_add()`

### Adding a New Built-in Tool

1. Add to `common/src/tools_builtin.c`:

```c
static eai_status_t tool_my_exec(const eai_kv_t *args, int arg_count, eai_tool_result_t *result) {
    // Implementation
    snprintf(result->data, sizeof(result->data), "{\"result\":\"ok\"}");
    result->len = strlen(result->data);
    return EAI_OK;
}

eai_status_t eai_tool_my_tool_register(eai_tool_registry_t *reg) {
    eai_tool_t tool = {0};
    strncpy(tool.name, "my.tool", EAI_TOOL_NAME_MAX - 1);
    tool.description = "My custom tool";
    tool.params[0] = (eai_tool_param_t){"input", EAI_PARAM_STRING, true};
    tool.param_count = 1;
    tool.exec = tool_my_exec;
    return eai_tool_register(reg, &tool);
}
```

2. Call it from `eai_tools_register_builtins()`
3. Declare in `common/include/eai/tools_builtin.h`

### Adding a New Connector

1. Create `framework/src/connector_myproto.c`
2. Implement `eai_connector_ops_t` (connect, disconnect, read, write)
3. Export: `extern const eai_connector_ops_t eai_connector_myproto_ops;`
4. Declare in `framework/include/eai_fw/connector.h`
5. Add to `framework/CMakeLists.txt`
6. Wire into CLI `cmd_run()` connector switch in `cli/src/main.c`

### Adding a New Deployment Profile

1. Create `profiles/my-profile/profile.yaml`
2. Add the preset to `eai_config_load_profile()` in `common/src/config.c`
3. Add it to the CLI help text in `cli/src/main.c`

### Adding a New Platform Adapter

1. Create `platform/src/platform_myos.c`
2. Implement `eai_platform_ops_t` functions
3. Export: `extern const eai_platform_ops_t eai_platform_myos_ops;`
4. Add build option in root `CMakeLists.txt`
5. Add to `platform/CMakeLists.txt`

---

## Key Design Patterns

### Vtable Pattern (Used Everywhere)

All pluggable components use C function pointer structs:

```
eai_runtime_ops_t    → runtime backends (llama.cpp, ONNX, TFLite)
eai_connector_ops_t  → protocol connectors (MQTT, OPC-UA, Modbus, CAN)
eai_platform_ops_t   → OS adapters (Linux, Windows, EoS)
```

This allows compile-time or runtime selection of implementations without dynamic linking.

### Manager Pattern

Components that hold multiple instances of the same type:

```
eai_tool_registry_t      → up to 64 tools
eai_fw_runtime_manager_t → up to 8 runtimes
eai_fw_connector_mgr_t   → up to 16 connectors
```

### Error Handling

Every function returns `eai_status_t`. Check against `EAI_OK`:

```c
eai_status_t s = eai_some_function(...);
if (s != EAI_OK) {
    EAI_LOG_ERROR("module", "failed: %s", eai_status_str(s));
    return s;
}
```

### Compile-Time Platform Selection

Platform-specific code uses `#ifdef _WIN32` / `#ifndef _WIN32` guards. Each platform file provides a stub for the opposite OS so both symbols always link.

---

## Resource Limits Summary

| Resource                  | Limit  | Where Defined              |
|---------------------------|--------|----------------------------|
| Tool registry capacity    | 64     | `EAI_TOOL_REGISTRY_MAX`    |
| Tool params per tool      | 16     | `EAI_TOOL_MAX_PARAMS`      |
| Tool permissions per tool | 8      | `EAI_TOOL_MAX_PERMISSIONS` |
| Min memory entries        | 128    | `EAI_MEM_MAX_ENTRIES`      |
| Framework memory entries  | 1024   | `EAI_FW_MEM_MAX_ENTRIES`   |
| Framework runtimes        | 8      | `EAI_FW_MAX_RUNTIMES`      |
| Connectors                | 16     | `EAI_CONNECTOR_MAX`        |
| Workflow steps            | 32     | `EAI_FW_MAX_WORKFLOW_STEPS`|
| Policy rules              | 32     | `EAI_POLICY_MAX_RULES`     |
| Observability metrics     | 128    | `EAI_OBS_MAX_METRICS`      |
| Observability spans       | 256    | `EAI_OBS_MAX_SPANS`        |
| Security permissions      | 32     | `EAI_PERM_MAX`             |
| Agent max iterations      | 10     | `EAI_AGENT_MAX_ITERATIONS` |
| Config max providers      | 8      | `EAI_CONFIG_MAX_PROVIDERS` |

# EoS SDK — Header-Only API Library

**Single `#include "eos_sdk.h"` for the entire EoS Embedded Operating System.**

[![Version](https://img.shields.io/badge/version-0.1.0-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()
[![Platform](https://img.shields.io/badge/platform-any-brightgreen)]()

## Quick Start

```c
#define EOS_SDK_ALL       // enable all modules (or pick specific ones below)
#include "eos_sdk.h"

int main(void) {
    eos_kernel_init();

    // Create a task
    int task = eos_task_create("blink", blink_led, NULL, 5, 1024);

    // Log
    EOS_INFO("EoS started, task=%d", task);

    // Read sensor
    eos_sensor_reading_t r;
    eos_sensor_read(0, &r);

    // SHA-256 hash
    char hex[65];
    eos_sha256_data("hello", 5, hex);

    eos_kernel_start();
}
```

## Installation

**Option 1: Copy header**
```bash
cp eos-sdk/include/eos_sdk.h your_project/include/
```

**Option 2: CMake FetchContent**
```cmake
include(FetchContent)
FetchContent_Declare(eos-sdk
    GIT_REPOSITORY https://github.com/embeddedos-org/eos-sdk.git
    GIT_TAG v0.1.0)
FetchContent_MakeAvailable(eos-sdk)
target_include_directories(myapp PRIVATE ${eos-sdk_SOURCE_DIR}/include)
```

**Option 3: ebuild SDK generator (for cross-compilation)**
```bash
ebuild sdk --target raspi4
source build/eos-sdk-raspi4/environment-setup
```

## Module Selection

Enable only what you need:

```c
// Pick specific modules
#define EOS_SDK_HAL
#define EOS_SDK_KERNEL
#define EOS_SDK_CRYPTO
#include "eos_sdk.h"

// Or enable everything
#define EOS_SDK_ALL
#include "eos_sdk.h"
```

| Define | Module | Description |
|---|---|---|
| `EOS_SDK_HAL` | HAL | GPIO, UART, SPI, I2C, CAN, PWM, ADC, Timer + 25 more |
| `EOS_SDK_KERNEL` | Kernel | RTOS tasks, mutex, semaphore, message queues, timers |
| `EOS_SDK_CRYPTO` | Crypto | SHA-256 (RFC 6234), AES-128/256, CRC32, RSA, ECC |
| `EOS_SDK_OTA` | OTA | A/B firmware update with SHA-256 verification |
| `EOS_SDK_SENSOR` | Sensor | Registry, calibration, filters (average, median, lowpass) |
| `EOS_SDK_MOTOR` | Motor | PID controller, speed/position modes, trajectory |
| `EOS_SDK_FILESYSTEM` | Filesystem | RAM/Flash FS with POSIX-like API |
| `EOS_SDK_LOGGING` | Logging | 6 levels, module filter, ring buffer, multi-output |
| `EOS_SDK_DEBUG` | Debug | GDB remote stub + core dump handler |
| `EOS_SDK_DRIVERS` | Drivers | Loadable driver framework (19 device classes) |
| `EOS_SDK_DEVICETREE` | DeviceTree | .dtb FDT parser |
| `EOS_SDK_SERVICES` | Services | Daemon lifecycle manager (start/stop/watchdog) |
| `EOS_SDK_NET` | Net | Networking abstraction |
| `EOS_SDK_POWER` | Power | Power management |
| `EOS_SDK_SECURITY` | Security | Keystore, ACL, secure boot |
| `EOS_SDK_ALL` | All | Enable everything |

---

## API Reference

### Kernel — RTOS Scheduler

```c
// Lifecycle
int  eos_kernel_init(void);
void eos_kernel_start(void);        // starts scheduler loop
bool eos_kernel_is_running(void);
void eos_kernel_tick(void);          // call from timer ISR

// Tasks — priority-based round-robin
int  eos_task_create(const char *name, void (*entry)(void*), void *arg,
                     uint8_t priority, uint32_t stack_size);  // returns handle
int  eos_task_delete(uint8_t handle);
int  eos_task_suspend(uint8_t handle);
int  eos_task_resume(uint8_t handle);
void eos_task_yield(void);
void eos_task_delay_ms(uint32_t ms);
uint8_t      eos_task_get_current(void);
eos_task_state_t eos_task_get_state(uint8_t handle);
const char  *eos_task_get_name(uint8_t handle);

// Mutex — recursive with ownership
int eos_mutex_create(uint8_t *out);
int eos_mutex_lock(uint8_t handle, uint32_t timeout_ms);
int eos_mutex_unlock(uint8_t handle);
int eos_mutex_delete(uint8_t handle);

// Semaphore — counting
int eos_sem_create(uint8_t *out, uint32_t initial, uint32_t max);
int eos_sem_wait(uint8_t handle, uint32_t timeout_ms);
int eos_sem_post(uint8_t handle);
int eos_sem_delete(uint8_t handle);
uint32_t eos_sem_get_count(uint8_t handle);

// Message Queue — typed ring buffer
int eos_queue_create(uint8_t *out, size_t item_size, uint32_t capacity);
int eos_queue_send(uint8_t handle, const void *item, uint32_t timeout_ms);
int eos_queue_receive(uint8_t handle, void *item, uint32_t timeout_ms);
int eos_queue_peek(uint8_t handle, void *item);
int eos_queue_delete(uint8_t handle);
uint32_t eos_queue_count(uint8_t handle);
bool eos_queue_is_full(uint8_t handle);
bool eos_queue_is_empty(uint8_t handle);
```

### Crypto — SHA-256, AES, CRC32

```c
// SHA-256 (RFC 6234 compliant)
void eos_sha256_init(EosSha256 *ctx);
void eos_sha256_update(EosSha256 *ctx, const void *data, size_t len);
void eos_sha256_final(EosSha256 *ctx, uint8_t digest[32]);
void eos_sha256_data(const void *data, size_t len, char hex[65]);  // one-shot
int  eos_sha256_file(const char *path, char hex[65]);
void eos_sha256_hex(const uint8_t digest[32], char hex[65]);

// AES-128/256
void eos_aes_init(EosAesCtx *ctx, const uint8_t *key, int key_bits);
void eos_aes_encrypt_block(const EosAesCtx *ctx, const uint8_t in[16], uint8_t out[16]);
void eos_aes_decrypt_block(const EosAesCtx *ctx, const uint8_t in[16], uint8_t out[16]);
void eos_aes_cbc_encrypt(const EosAesCtx *ctx, const uint8_t *iv,
                         const uint8_t *in, uint8_t *out, size_t len);

// CRC32
uint32_t eos_crc32(uint32_t crc, const void *data, size_t len);
```

### OTA — Firmware Update

```c
int  eos_ota_init(void);
int  eos_ota_begin(const eos_ota_source_t *source);
int  eos_ota_write_chunk(const uint8_t *data, size_t len);
int  eos_ota_finish(void);
int  eos_ota_verify(void);    // SHA-256 hash check
int  eos_ota_apply(void);     // switch to updated slot
int  eos_ota_rollback(void);  // revert to previous slot
eos_ota_slot_t eos_ota_get_active_slot(void);  // SLOT_A or SLOT_B
```

### Sensor — Read, Calibrate, Filter

```c
int eos_sensor_init(void);
int eos_sensor_register(const eos_sensor_config_t *cfg);
int eos_sensor_read(uint8_t id, eos_sensor_reading_t *reading);
int eos_sensor_read_filtered(uint8_t id, eos_sensor_reading_t *reading);
int eos_sensor_calibrate(uint8_t id, const eos_sensor_calib_t *calib);
int eos_sensor_set_filter(uint8_t id, eos_filter_type_t filter, uint8_t window);
// Filters: EOS_FILTER_NONE, EOS_FILTER_AVERAGE, EOS_FILTER_MEDIAN, EOS_FILTER_LOWPASS
```

### Motor — PID Control

```c
int  eos_motor_ctrl_init(void);
int  eos_motor_ctrl_configure(const eos_motor_ctrl_config_t *cfg);
int  eos_motor_ctrl_set_speed(uint8_t id, int16_t speed);
int  eos_motor_ctrl_set_position(uint8_t id, int32_t position);
int  eos_motor_ctrl_stop(uint8_t id);
int  eos_motor_ctrl_emergency_stop(uint8_t id);
void eos_motor_ctrl_update(void);  // call from control loop timer
```

### Filesystem — POSIX-like API

```c
int  eos_fs_init(const eos_fs_config_t *cfg);
eos_file_t eos_fs_open(const char *path, uint32_t flags);
// Flags: EOS_O_READ | EOS_O_WRITE | EOS_O_CREATE | EOS_O_APPEND | EOS_O_TRUNC
int  eos_fs_read(eos_file_t fd, void *buf, size_t len);
int  eos_fs_write(eos_file_t fd, const void *data, size_t len);
int  eos_fs_seek(eos_file_t fd, int32_t offset, eos_seek_whence_t whence);
int  eos_fs_close(eos_file_t fd);
int  eos_fs_mkdir(const char *path);
int  eos_fs_remove(const char *path);
int  eos_fs_rename(const char *old, const char *new);
bool eos_fs_exists(const char *path);
```

### Logging — Runtime Level Control

```c
// Set level at runtime (no recompile)
eos_log_set_level(EOS_LOG_DEBUG);

// Module-scoped filtering
eos_log_set_module_level("hal", EOS_LOG_WARN);

// Log macros
EOS_TRACE("entering function %s", __func__);
EOS_DEBUG("value=%d", x);
EOS_INFO("initialized");
EOS_WARN("low battery: %d%%", pct);
EOS_ERROR("sensor read failed: %d", err);
EOS_FATAL("stack overflow in task %s", name);

// Ring buffer (crash analysis)
eos_log_ring_dump();  // print last 64 log entries

// Output targets
eos_log_set_output(EOS_LOG_OUTPUT_STDERR | EOS_LOG_OUTPUT_UART);
```

### Debug — GDB Stub + Core Dump

```c
// GDB remote debugging
EosGdbStub stub;
eos_gdb_init(&stub, EOS_GDB_TRANSPORT_TCP);
eos_gdb_start(&stub, 3333);   // listen on port 3333
eos_gdb_add_breakpoint(&stub, 0x08001000);
eos_gdb_breakpoint();          // trigger breakpoint (BKPT/INT3/EBREAK)

// Core dump (call from fault handler)
eos_coredump_init(EOS_DUMP_TARGET_RAM);
eos_coredump_capture(EOS_CRASH_HARDFAULT, &regs);
eos_coredump_print(&dump);     // print register dump + stack trace
```

### Drivers — Loadable Framework

```c
EosDrvRegistry reg;
eos_drv_init(&reg);
eos_drv_register(&reg, &my_uart_driver);  // probe/bind/unbind lifecycle
eos_drv_probe_all(&reg);
EosDriver *d = eos_drv_find_by_class(&reg, EOS_DRV_CLASS_UART, 0);
eos_drv_ioctl(&reg, "my_uart", CMD_SET_BAUD, &baud);
// 19 classes: GPIO, UART, SPI, I2C, CAN, PWM, ADC, DAC, Timer, DMA,
//             Ethernet, USB, SDIO, Display, Sensor, Storage, Network, Audio, Camera
```

### Service Manager — Daemon Lifecycle

```c
EosSvcManager mgr;
eos_svc_init(&mgr);
eos_svc_register(&mgr, "ebot_server", &ebot_ops);
eos_svc_register(&mgr, "sensor_daemon", &sensor_ops);
eos_svc_add_dependency(&mgr, "sensor_daemon", "ebot_server");
eos_svc_set_restart_policy(&mgr, "ebot_server", EOS_SVC_RESTART_ON_FAIL, 3, 1000);
eos_svc_set_watchdog(&mgr, "ebot_server", 30000);
eos_svc_start_all(&mgr);  // starts in dependency order
// In main loop:
eos_svc_tick(&mgr, now_ms);  // health checks + auto-restart
```

---

## Supported Platforms

| Architecture | Targets | Class |
|---|---|---|
| ARM Cortex-M | STM32F4, STM32H7, nRF52, RP2040 | MCU |
| ARM Cortex-A | Raspberry Pi 3/4, i.MX8M, AM64x, VExpress | SBC/SoC |
| RISC-V | SiFive FU740, QEMU virt | SBC/Virtual |
| MIPS | Malta | DevBoard |
| x86_64 | PC, servers, QEMU q35 | PC/Virtual |

## Ecosystem

| Repo | Description |
|---|---|
| [eos](https://github.com/embeddedos-org/eos) | Core OS — implementations for all SDK APIs |
| [eboot](https://github.com/embeddedos-org/eboot) | Bootloader — 26 board ports, secure boot |
| [ebuild](https://github.com/embeddedos-org/ebuild) | Build system — SDK generator, deliverable packager |
| [eipc](https://github.com/embeddedos-org/eipc) | Secure IPC — Go + C SDK |
| [eai](https://github.com/embeddedos-org/eai) | AI layer — LLM models, Ebot server |
| [eni](https://github.com/embeddedos-org/eni) | Neural interface — Neuralink adapter |
| [eApps](https://github.com/embeddedos-org/eApps) | Dev tools — Ebot client, GUI apps |

## License

MIT
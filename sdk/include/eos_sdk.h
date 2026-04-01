// SPDX-License-Identifier: MIT
// Copyright (c) 2026 EoS Project
// ISO/IEC 25000 | ISO/IEC/IEEE 15288:2023

/**
 * @file eos_sdk.h
 * @brief EoS SDK — Unified API for the Embedded Operating System
 * @version 0.1.0
 *
 * Single-include header-only SDK providing access to ALL EoS APIs.
 * Include this file and enable the modules you need via preprocessor defines.
 *
 * Usage:
 *   #define EOS_SDK_HAL          // Hardware Abstraction Layer
 *   #define EOS_SDK_KERNEL       // RTOS Kernel (tasks, mutex, semaphore, IPC)
 *   #define EOS_SDK_CRYPTO       // SHA-256, AES, CRC32, RSA
 *   #define EOS_SDK_OTA          // Over-the-Air firmware update
 *   #define EOS_SDK_SENSOR       // Sensor framework with filters
 *   #define EOS_SDK_MOTOR        // PID motor control
 *   #define EOS_SDK_FILESYSTEM   // RAM/Flash filesystem
 *   #define EOS_SDK_LOGGING      // Enhanced logging (6 levels, ring buffer)
 *   #define EOS_SDK_DEBUG        // GDB stub + core dump handler
 *   #define EOS_SDK_DRIVERS      // Loadable driver framework
 *   #define EOS_SDK_DEVICETREE   // Device tree (.dtb) parser
 *   #define EOS_SDK_SERVICES     // Service manager (daemon lifecycle)
 *   #define EOS_SDK_NET          // Networking abstraction
 *   #define EOS_SDK_POWER        // Power management
 *   #define EOS_SDK_SECURITY     // Security services
 *   #define EOS_SDK_ALL          // Enable everything
 *   #include "eos_sdk.h"
 *
 * Platform: Any (Linux, RTOS, bare-metal)
 * License: MIT
 * Website: https://embeddedos-org.github.io
 */
#ifndef EOS_SDK_H
#define EOS_SDK_H

#define EOS_SDK_VERSION_MAJOR 0
#define EOS_SDK_VERSION_MINOR 1
#define EOS_SDK_VERSION_PATCH 0
#define EOS_SDK_VERSION       "0.1.0"

/* Enable all modules if EOS_SDK_ALL is defined */
#ifdef EOS_SDK_ALL
#define EOS_SDK_HAL
#define EOS_SDK_KERNEL
#define EOS_SDK_CRYPTO
#define EOS_SDK_OTA
#define EOS_SDK_SENSOR
#define EOS_SDK_MOTOR
#define EOS_SDK_FILESYSTEM
#define EOS_SDK_LOGGING
#define EOS_SDK_DEBUG
#define EOS_SDK_DRIVERS
#define EOS_SDK_DEVICETREE
#define EOS_SDK_SERVICES
#define EOS_SDK_NET
#define EOS_SDK_POWER
#define EOS_SDK_SECURITY
#endif

/* ============================================================
 * Core Configuration (always included)
 * ============================================================ */
#include "eos/eos_config.h"

/* ============================================================
 * HAL — Hardware Abstraction Layer (33 peripherals)
 *
 * GPIO, UART, SPI, I2C, CAN, PWM, ADC, DAC, Timer, DMA,
 * USB, Ethernet, SDIO, Display, Camera, Audio, and more.
 *
 * API:
 *   eos_hal_gpio_init/read/write/toggle
 *   eos_hal_uart_init/read/write
 *   eos_hal_spi_init/transfer
 *   eos_hal_i2c_init/read/write
 *   eos_hal_pwm_init/set_duty/set_freq
 *   eos_hal_adc_init/read
 *   eos_hal_timer_init/start/stop
 * ============================================================ */
#ifdef EOS_SDK_HAL
#include "eos/hal.h"
#include "eos/hal_extended.h"
#endif

/* ============================================================
 * Kernel — RTOS Task Scheduler + Sync + IPC
 *
 * Round-robin scheduler with priority, recursive mutex,
 * counting semaphore, typed message queues, software timers.
 *
 * API:
 *   eos_kernel_init/start
 *   eos_task_create(name, entry, arg, priority, stack_size) -> handle
 *   eos_task_delete/suspend/resume/yield/delay_ms
 *   eos_mutex_create/lock/unlock/delete
 *   eos_sem_create/wait/post/delete/get_count
 *   eos_queue_create/send/receive/peek/delete/count
 *   eos_swtimer_create/start/stop/reset/delete
 * ============================================================ */
#ifdef EOS_SDK_KERNEL
#include "eos/kernel.h"
#include "eos/multicore.h"
#endif

/* ============================================================
 * Crypto — SHA-256, AES, CRC32, RSA, ECC
 *
 * SHA-256 is RFC 6234 compliant with NIST test vectors.
 *
 * API:
 *   eos_sha256_init/update/final/data/file/hex
 *   eos_aes_init/encrypt_block/decrypt_block/cbc_encrypt/cbc_decrypt
 *   eos_crc32(crc, data, len) -> uint32_t
 *   eos_rsa_sign_sha256/eos_rsa_verify_sha256
 * ============================================================ */
#ifdef EOS_SDK_CRYPTO
#include "eos/crypto.h"
#endif

/* ============================================================
 * OTA — Over-the-Air Firmware Update
 *
 * A/B slot management with SHA-256 firmware verification.
 *
 * API:
 *   eos_ota_init/deinit
 *   eos_ota_check_update/begin/write_chunk/finish
 *   eos_ota_verify -> compares SHA-256 hash
 *   eos_ota_apply/rollback
 *   eos_ota_get_active_slot/set_active_slot/mark_slot_valid
 * ============================================================ */
#ifdef EOS_SDK_OTA
#include "eos/ota.h"
#endif

/* ============================================================
 * Sensor — Unified Sensor Framework with Filters
 *
 * Register sensors, read with calibration, apply digital filters
 * (moving average, median, low-pass).
 *
 * API:
 *   eos_sensor_init/deinit
 *   eos_sensor_register/unregister
 *   eos_sensor_read/read_filtered
 *   eos_sensor_calibrate/auto_calibrate
 *   eos_sensor_set_filter(id, EOS_FILTER_AVERAGE|MEDIAN|LOWPASS, window)
 * ============================================================ */
#ifdef EOS_SDK_SENSOR
#include "eos/sensor.h"
#endif

/* ============================================================
 * Motor — PID Motor Control
 *
 * Closed-loop speed and position control with PID, trajectory
 * planning, and encoder feedback.
 *
 * API:
 *   eos_motor_ctrl_init/configure/remove
 *   eos_motor_ctrl_set_speed/set_position/move_relative
 *   eos_motor_ctrl_stop/emergency_stop/reset_position
 *   eos_motor_ctrl_set_pid_speed/set_pid_position
 *   eos_motor_ctrl_update -> call from control loop
 * ============================================================ */
#ifdef EOS_SDK_MOTOR
#include "eos/motor_ctrl.h"
#endif

/* ============================================================
 * Filesystem — RAM/Flash File System
 *
 * POSIX-like API over RAM, LittleFS, SPIFFS, or FAT.
 *
 * API:
 *   eos_fs_init/deinit/format/stat
 *   eos_fs_open(path, EOS_O_READ|WRITE|CREATE|APPEND|TRUNC)
 *   eos_fs_read/write/seek/tell/truncate/sync/close
 *   eos_fs_mkdir/opendir/readdir/closedir
 *   eos_fs_remove/rename/exists
 * ============================================================ */
#ifdef EOS_SDK_FILESYSTEM
#include "eos/filesystem.h"
#endif

/* ============================================================
 * Logging — Enhanced Runtime Logging
 *
 * 6 levels (TRACE→FATAL), module-scoped filtering, ring buffer
 * for crash analysis, multi-output (stderr, UART, file).
 *
 * API:
 *   eos_log_set_level/get_level -> runtime, no recompile
 *   eos_log_set_module_level("hal", EOS_LOG_DEBUG)
 *   EOS_TRACE/DEBUG/INFO/WARN/ERROR/FATAL(...)
 *   eos_log_ring_count/get/dump/clear
 *   eos_log_set_output(EOS_LOG_OUTPUT_STDERR | EOS_LOG_OUTPUT_UART)
 * ============================================================ */
#ifdef EOS_SDK_LOGGING
#include "eos/log.h"
#endif

/* ============================================================
 * Debug — GDB Remote Stub + Core Dump Handler
 *
 * GDB stub: full RSP protocol over UART/TCP, 16 breakpoints.
 * Core dump: crash capture with CRC32 validation.
 *
 * API:
 *   eos_gdb_init/start/stop/handle_exception
 *   eos_gdb_add_breakpoint/remove_breakpoint/clear_breakpoints
 *   eos_gdb_breakpoint() -> trigger programmatic breakpoint
 *   eos_coredump_init/capture/save/load/print/clear
 *   eos_coredump_validate -> CRC32 check
 * ============================================================ */
#ifdef EOS_SDK_DEBUG
#include "eos/gdb_stub.h"
#include "eos/coredump.h"
#endif

/* ============================================================
 * Drivers — Loadable Driver Framework
 *
 * 19 device classes, probe/bind/unbind, suspend/resume,
 * vendor/device ID and compatible string matching.
 *
 * API:
 *   eos_drv_init/shutdown
 *   eos_drv_register/unregister
 *   eos_drv_probe/probe_all/unbind
 *   eos_drv_find/find_by_class/find_by_match
 *   eos_drv_suspend_all/resume_all
 *   eos_drv_ioctl(name, cmd, arg)
 * ============================================================ */
#ifdef EOS_SDK_DRIVERS
#include "eos/driver.h"
#endif

/* ============================================================
 * Device Tree — .dtb FDT Parser
 *
 * Parse flattened device tree blobs for hardware description.
 *
 * API:
 *   eos_dt_parse(dt, dtb_data, size)
 *   eos_dt_find(dt, "/soc/uart@40000000")
 *   eos_dt_find_compatible(dt, "arm,pl011")
 *   eos_dt_get_prop/get_u32/get_string/get_reg/get_irq
 *   eos_dt_walk(dt, callback, ctx)
 * ============================================================ */
#ifdef EOS_SDK_DEVICETREE
#include "devicetree.h"
#endif

/* ============================================================
 * Service Manager — Daemon Lifecycle
 *
 * Start/stop/restart services with dependency ordering,
 * watchdog timeout, health checks, auto-restart.
 *
 * API:
 *   eos_svc_init/start_all/stop_all/tick
 *   eos_svc_register(mgr, "ebot", &ops)
 *   eos_svc_start/stop/restart
 *   eos_svc_set_restart_policy(NEVER|ALWAYS|ON_FAIL, max, delay)
 *   eos_svc_set_watchdog(name, timeout_ms)
 *   eos_svc_add_dependency(name, depends_on)
 * ============================================================ */
#ifdef EOS_SDK_SERVICES
#include "eos/service.h"
#endif

/* ============================================================
 * Networking — Abstraction Layer
 * ============================================================ */
#ifdef EOS_SDK_NET
#include "eos/net.h"
#endif

/* ============================================================
 * Power — Power Management
 * ============================================================ */
#ifdef EOS_SDK_POWER
#include "eos/power.h"
#endif

/* ============================================================
 * Security — Keystore, ACL, Secure Boot
 * ============================================================ */
#ifdef EOS_SDK_SECURITY
#include "eos/security.h"
#endif

#endif /* EOS_SDK_H */
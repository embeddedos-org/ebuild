# eBootloader Architecture

## Staged Boot Architecture

```
ROM / Reset Vector
   ↓
eBootloader   (stage-0 / minimal core)
   ↓
E-Boot         (stage-1 boot manager)
   ↓
Application Firmware
   ↕
EoS Firmware Services
```

## Module Map

| Module        | Layer   | Role                                      |
|---------------|---------|-------------------------------------------|
| `stage0/`     | Stage-0 | Reset entry, minimal HW init, recovery check, jump to stage-1 |
| `stage1/`     | Stage-1 | Image scan, boot policy, boot log, jump to application |
| `core/`       | Shared  | Boot control, image verify, slot management, recovery state machine, firmware services |
| `hal/`        | HAL     | Board-agnostic flash/watchdog/UART/jump wrappers |
| `boards/`     | BSP     | Board-specific register-level implementations |
| `include/`    | API     | All public headers and type definitions |
| `tools/`      | Host    | Image packer, signing tool, UART recovery client |
| `tests/`      | Test    | Host-side unit tests with simulated flash |

## Flash Memory Map (STM32F407 Reference)

```
Address Range              Size    Region
─────────────────────────────────────────────────────
0x08000000 - 0x08003FFF    16K     Stage-0 (eBootloader)
0x08004000 - 0x0800FFFF    48K     Stage-1 (E-Boot)
0x08010000 - 0x0807FFFF    448K    Slot A (active firmware)
0x08080000 - 0x080EFFFF    448K    Slot B (candidate firmware)
0x080F0000 - 0x080F3FFF    16K     Recovery image
0x080F4000 - 0x080F5FFF    8K      Boot control (primary)
0x080F6000 - 0x080F7FFF    8K      Boot control (backup)
0x080F8000 - 0x080F9FFF    8K      Boot log
0x080FA000 - 0x080FFFFF    24K     Device config / reserved
```

## Boot Flow

```
Reset_Handler()
  ├── Copy .data, zero .bss
  ├── ebldr_hw_init_minimal()
  │   ├── board_get_ops() → register HAL
  │   └── board_early_init() → clocks, flash latency
  └── ebldr_stage0_main()
      ├── ebldr_watchdog_init()
      ├── eos_bootctl_load() → load boot state
      ├── ebldr_recovery_triggered()?
      │   └── YES → eos_recovery_enter() → UART command loop
      └── jump to stage-1 → eboot_main()
          ├── eos_bootctl_load()
          ├── eos_boot_log_init()
          ├── eboot_should_recover()?
          │   └── YES → eos_recovery_enter()
          ├── eboot_scan_images() → verify both slots
          ├── eboot_select_slot() → boot policy
          │   ├── Check max attempts → rollback
          │   ├── Check pending upgrade → test boot
          │   ├── Try active slot
          │   └── Fallback to alternate slot
          └── eboot_jump_to_app()
              ├── Increment boot attempts
              ├── Disable interrupts
              ├── Deinit peripherals
              └── Jump to application vector table
```

## Rollback Sequence

```
1. Application writes new image → Slot B
2. eos_fw_request_upgrade(SLOT_B, EOS_UPGRADE_TEST)
3. system_reboot()
4. E-Boot sees pending_slot = B, flags = TEST_BOOT
5. Verifies Slot B image → boots Slot B
6. boot_attempts++
7. New firmware runs self-test
8. eos_fw_confirm_running_image() → marks CONFIRMED
   OR
   Firmware crashes / fails self-test
   → Watchdog resets → boot_attempts++
   → After max_attempts reached → E-Boot rolls back to Slot A
```

## Recovery Protocol (UART)

| Command   | Code | Description                     |
|-----------|------|---------------------------------|
| PING      | 0x01 | Identity check — returns "EOS"  |
| INFO      | 0x02 | Flash layout and slot addresses |
| ERASE     | 0x03 | Erase target slot               |
| WRITE     | 0x04 | Write chunk to slot             |
| VERIFY    | 0x05 | Verify slot image integrity     |
| BOOT      | 0x06 | Set active slot and reboot      |
| LOG       | 0x07 | Dump boot log                   |
| RESET     | 0x08 | System reset                    |
| FACTORY   | 0x09 | Erase all + reset defaults      |

Packet format: `[cmd:1][slot:1][len:2][offset:4]`

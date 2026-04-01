# eBootloader Update Flow

## Overview

eBootloader supports three firmware update strategies. This document
describes the recommended OTA workflow (firmware-owned download,
bootloader-owned activation).

## OTA Update Sequence

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Cloud /    │     │ Application │     │  E-Boot     │
│   Server     │     │  Firmware   │     │  (Stage-1)  │
└──────┬───────┘     └──────┬──────┘     └──────┬──────┘
       │                    │                    │
       │  1. New version    │                    │
       │    available       │                    │
       │ ──────────────────>│                    │
       │                    │                    │
       │  2. Download       │                    │
       │    image chunks    │                    │
       │ ──────────────────>│                    │
       │                    │                    │
       │                    │ 3. Write to        │
       │                    │    inactive slot   │
       │                    │ (Slot B)           │
       │                    │                    │
       │                    │ 4. Request         │
       │                    │    test boot       │
       │                    │ eos_fw_request_    │
       │                    │ upgrade(B, TEST)   │
       │                    │                    │
       │                    │ 5. Reboot          │
       │                    │ ──────────────────>│
       │                    │                    │
       │                    │                    │ 6. Verify Slot B
       │                    │                    │    image
       │                    │                    │
       │                    │                    │ 7. Boot Slot B
       │                    │                    │    (test mode)
       │                    │                    │
       │                    │ 8. Self-test       │
       │                    │<───────────────────│
       │                    │                    │
       │                    │ 9. eos_fw_confirm_ │
       │                    │    running_image() │
       │                    │                    │
       │                    │    ── OR ──        │
       │                    │                    │
       │                    │ 9b. Crash /        │
       │                    │     watchdog       │
       │                    │     → rollback     │
       │                    │                    │
```

## Application Code Example

### Requesting an Update

```c
int do_ota_update(const uint8_t *image_data, size_t image_len)
{
    eos_slot_t target = EOS_SLOT_B;
    uint32_t addr = eos_hal_slot_addr(target);

    /* Erase target slot */
    eos_hal_flash_erase(addr, eos_hal_slot_size(target));

    /* Write image (header + payload) */
    eos_hal_flash_write(addr, image_data, image_len);

    /* Request test boot */
    int rc = eos_fw_request_upgrade(target, EOS_UPGRADE_TEST);
    if (rc != EOS_OK) return rc;

    /* Reboot to apply */
    eos_hal_system_reset();
    return EOS_OK; /* unreachable */
}
```

### Confirming After Self-Test

```c
int app_startup(void)
{
    if (eos_fw_is_test_boot()) {
        if (self_test_passed()) {
            eos_fw_confirm_running_image();
        } else {
            /* Don't confirm — let watchdog trigger rollback */
            eos_fw_request_recovery();
            eos_hal_system_reset();
        }
    }
    return 0;
}
```

## Rollback Triggers

| Trigger                          | Result                         |
|----------------------------------|--------------------------------|
| Unconfirmed test boot + reboot   | boot_attempts incremented      |
| boot_attempts ≥ max_attempts     | Automatic rollback to Slot A   |
| Watchdog reset during test boot  | boot_attempts incremented      |
| No valid image in active slot    | Fallback to alternate slot     |
| No valid image in either slot    | Enter recovery mode            |

## Anti-Tearing Protection

The boot control block is written to **two separate flash sectors**
(primary and backup). The write sequence is:

1. Compute CRC32 of new boot control data
2. Erase primary sector
3. Write primary sector
4. Erase backup sector
5. Write backup sector

On load, if the primary copy fails CRC validation, the backup is used.
This protects against power loss during metadata updates.

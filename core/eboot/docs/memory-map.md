# eBootloader Memory Map

## Default Layout (STM32F407, 1MB Flash)

```
┌──────────────────────────────────────────────────────────┐
│ 0x08000000  Stage-0 (eBootloader)              16 KB   │
├──────────────────────────────────────────────────────────┤
│ 0x08004000  Stage-1 (E-Boot)                    48 KB   │
├──────────────────────────────────────────────────────────┤
│ 0x08010000  Slot A (Active Firmware)            448 KB   │
├──────────────────────────────────────────────────────────┤
│ 0x08080000  Slot B (Candidate Firmware)         448 KB   │
├──────────────────────────────────────────────────────────┤
│ 0x080F0000  Recovery Image (Golden)              16 KB   │
├──────────────────────────────────────────────────────────┤
│ 0x080F4000  Boot Control (Primary)                8 KB   │
├──────────────────────────────────────────────────────────┤
│ 0x080F6000  Boot Control (Backup)                 8 KB   │
├──────────────────────────────────────────────────────────┤
│ 0x080F8000  Boot Log                              8 KB   │
├──────────────────────────────────────────────────────────┤
│ 0x080FA000  Device Config / Reserved             24 KB   │
└──────────────────────────────────────────────────────────┘
```

## Design Rules

1. **Stage-0 is never updated in the field** — it must remain immutable
   after manufacturing to guarantee recovery is always possible.

2. **Boot control is dual-copied** — primary at 0x080F4000, backup at
   0x080F6000. Both carry CRC32 protection. On load, if primary is
   corrupt the backup is used.

3. **Slot A and Slot B are identical in size** — this simplifies the
   swap/upgrade logic and allows either slot to be active.

4. **Recovery image is optional but recommended** — on flash-constrained
   devices, Slot B can double as recovery storage.

5. **Boot log is a circular buffer** — the `log_head` field in the boot
   control block tracks the write position.

## Adapting to Other MCUs

To port to a different MCU, create a new `boards/<mcu>/` directory and:

1. Define the memory map addresses in a board header
2. Implement `eos_board_ops_t` with appropriate flash/watchdog/UART drivers
3. Create linker scripts for stage-0 and stage-1
4. Provide `board_early_init()` and `board_get_ops()`

Example for nRF52840 (1MB Flash, 256KB RAM):

```
Stage-0:     0x00000000 - 0x00003FFF  (16K)
Stage-1:     0x00004000 - 0x0000FFFF  (48K)
Slot A:      0x00010000 - 0x0007FFFF  (448K)
Slot B:      0x00080000 - 0x000EFFFF  (448K)
Boot Ctrl:   0x000F0000 - 0x000F1FFF  (8K)
Boot Backup: 0x000F2000 - 0x000F3FFF  (8K)
Boot Log:    0x000F4000 - 0x000F5FFF  (8K)
Reserved:    0x000F6000 - 0x000FFFFF  (40K)
```

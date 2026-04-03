# ebuild AI — Supported Input Formats & Capabilities

This document describes what the ebuild hardware analyzer can and cannot process, so you know exactly what to expect.

---

## Supported Inputs

### 1. Plain Text Description ✅ (Primary — Recommended)

The **best supported** input. Describe your hardware in natural language.

```bash
ebuild analyze "nRF52840 BLE sensor with I2C temperature and SPI flash, 1MB flash, 256KB RAM"
```

**What it extracts:**
- MCU identification (100+ MCUs in the database across 16 architectures)
- Peripheral detection (24 peripheral types via keyword matching)
- Component identification (200+ part numbers via component database)
- Memory sizes (flash, RAM — parsed from "512KB flash", "1MB RAM", etc.)
- Clock speed (parsed from "64 MHz", "240MHz", etc.)

### 2. YAML Hardware Description Files ✅

```bash
ebuild analyze hardware/board/sample_iot_gateway.yaml
```

Read as text + component database search. Works with any YAML format.

### 3. KiCad Schematic Files ✅ (Full S-Expression Parsing)

```bash
ebuild analyze my_design.kicad_sch
```

**What it does:**
- Parses KiCad 6/7/8 `.kicad_sch` files using a proper S-expression parser
- Extracts component symbols (reference, value, footprint, library)
- Traces net connectivity (which pins connect to which nets via labels)
- Identifies peripherals from net names (SDA → I2C, MOSI → SPI, etc.)
- Looks up component part numbers in the 200+ component database
- Auto-detects MCU from component values

### 4. Eagle / Autodesk Schematic Files ✅ (XML Parsing)

```bash
ebuild analyze my_design.sch
```

**What it does:**
- Parses Eagle `.sch` XML files (including Autodesk Fusion/EAGLE)
- Extracts parts with library, deviceset, device, and package info
- Traces signal/net connections via `<pinref>` elements
- Resolves packages from library definitions
- Component database lookup on all part values

### 5. BOM (Bill of Materials) CSV ✅ (Component Database Lookup)

```bash
ebuild analyze bom_export.csv
```

**What it does:**
- Parses CSV lines for component references, values, and descriptions
- Looks up every part number against the **200+ component database**
- Identifies peripherals including I2C addresses, bus types, and vendors

**Example — what the component DB recognizes:**
```csv
Ref, Value, Description
U1, NRF52840, Nordic BLE SoC             → MCU: nRF52840, arch: ARM, core: Cortex-M4F
U2, TMP102, Temperature sensor            → I2C sensor, addr: 0x48, vendor: TI
U3, W25Q128, SPI Flash                    → SPI flash storage, vendor: Winbond
U4, MPU6050, IMU                          → I2C IMU, addr: 0x68, vendor: InvenSense
U5, SSD1306, OLED Display                 → I2C display, addr: 0x3C
U6, SX1276, LoRa Module                   → SPI LoRa radio, vendor: Semtech
```

### 6. Auto-Format Detection ✅

```bash
# The analyzer auto-detects format by file extension:
ebuild analyze design.kicad_sch   # → KiCad parser
ebuild analyze design.sch         # → Eagle XML or KiCad (auto-detected)
ebuild analyze bom.csv            # → BOM parser + component DB
ebuild analyze spec.yaml          # → Text + component DB
ebuild analyze notes.txt          # → Text + component DB
```

### 7. LLM-Enhanced Analysis ✅ (Integrated — Optional)

```bash
# Auto-detects Ollama (local) or uses OPENAI_API_KEY from environment
ebuild analyze "nRF52840 BLE sensor" --llm

# Explicit provider
ebuild analyze design.kicad_sch --llm-provider ollama --llm-model llama3
ebuild analyze design.kicad_sch --llm-provider openai --llm-model gpt-4o
```

**LLM Provider Auto-Detection:**
1. **Ollama** (local, free) — checks `http://localhost:11434`
2. **OpenAI** — uses `OPENAI_API_KEY` env var
3. **Custom** — uses `EOS_LLM_API_KEY` + `EOS_LLM_URL` + `EOS_LLM_MODEL` env vars
4. **None** — works without LLM (rule engine only)

---

## NOT Supported (Today)

| Format | Why Not | Workaround |
|--------|---------|-----------|
| **Altium Designer** (`.SchDoc`, `.PcbDoc`) | Binary/proprietary format | Export BOM as CSV → use BOM input |
| **OrCAD / Cadence** (`.dsn`, `.brd`) | Binary format | Export BOM as CSV → use BOM input |
| **Gerber files** (`.gbr`, `.drl`) | PCB fabrication data, no component info | Not applicable — use schematic source |
| **PDF datasheets** | No PDF parser | Read the datasheet yourself, describe in text |
| **STEP / 3D CAD** (`.step`, `.iges`) | Mechanical, no electrical info | Not applicable |
| **KiCad netlists** (`.kicad_net`) | Not yet parsed | Use `.kicad_sch` — it has full component + net data |
| **KiCad PCB** (`.kicad_pcb`) | Layout file, limited component data | Use `.kicad_sch` instead |
| **SystemVerilog / VHDL** | HDL, not PCB design | Describe the target FPGA/SoC in text |

---

## What the Analyzer Produces

Regardless of input format, the output is always the same — 4 files:

| Output | Format | Used By |
|--------|--------|---------|
| `board.yaml` | YAML | eos build system |
| `boot.yaml` | YAML | eboot build system |
| `eos_product_config.h` | C header | eos compiler flags |
| `eboot_flash_layout.h` | C header | eboot linker |

---

## How the Rule Engine Works

The analyzer uses a **deterministic rule engine** — no server, no API key, no neural network.

```
Input (text/YAML/KiCad/BOM)
    │
    ▼
┌──────────────────────┐
│  MCU Database Lookup  │  100+ MCUs across 16 architectures
│  (keyword matching)   │  "nrf52840" → ARM, Cortex-M4F, Nordic
└──────────┬───────────┘
           │
    ▼
┌──────────────────────┐
│  Peripheral Keywords  │  24 peripheral types
│  (regex matching)     │  "ble" → EOS_ENABLE_BLE
└──────────┬───────────┘
           │
    ▼
┌──────────────────────┐
│  Memory/Clock Regex   │  "512KB flash" → flash_size = 524288
│  (pattern matching)   │  "64 MHz" → clock_hz = 64000000
└──────────┬───────────┘
           │
    ▼
  HardwareProfile
    │
    ▼
  Config Generation (board.yaml, boot.yaml, .h files)
```

### MCU Database Coverage

| Architecture | MCUs in Database | Examples |
|-------------|-----------------|---------|
| ARM Cortex-M | STM32F4, STM32H7, STM32MP1, nRF52, nRF52840, SAMD51, RP2040 | 7 families |
| ARM Cortex-A | i.MX8M, AM64x | 2 families |
| ARM Legacy | StrongARM (SA110, SA1100, SA1110), XScale (PXA250-270, IXP420-465) | 9 MCUs |
| RISC-V | SiFive E/U, GD32VF103 | 3 MCUs |
| Xtensa | ESP32 | 1 family |
| x86 | i386, i486, Pentium, Atom, Quark, x86_64 | 6 MCUs |
| MIPS | MIPS32, MIPS64, MIPS24K, PIC32, JZ4740, AR9331 | 7 MCUs |
| PowerPC | MPC8xx, MPC5200, MPC5554, MPC8540, P1020, P2020, PPC440, PPC405 | 10 MCUs |
| M68K / ColdFire | MC68000-68060, MCF5206-54418 | 14 MCUs |
| SPARC | SPARC V7/V8/V9, LEON3/4, UT699, GR712RC, ERC32 | 7 MCUs |
| SuperH | SH7091-7751 (SH4), SH7709-7710 (SH3), SH7203-7206 (SH2A) | 8 MCUs |
| H8/300 | H8/300H, H8S2148, H8S2368, H83048, H83069 | 5 MCUs |
| V850 | V850, V850E/E2/ES, RH850, UPD70F3002 | 6 MCUs |
| FR-V | FR400-550, MB93091, MB93493 | 6 MCUs |
| MN103 | MN1030, MN103S, AM33, AM34 | 4 MCUs |

**Total: 100+ MCUs recognized**

---

## Optional: LLM-Enhanced Analysis

After the rule engine runs, ebuild can generate an **LLM prompt** for deeper analysis:

```python
from ebuild.eos_ai.eos_hw_analyzer import EosHardwareAnalyzer

analyzer = EosHardwareAnalyzer()
profile = analyzer.interpret_text("nRF52840 BLE sensor with I2C and SPI")
prompt = analyzer.generate_prompt(profile)
print(prompt)  # paste this into any LLM
```

The generated prompt asks the LLM for:
1. Recommended EoS product profile
2. Boot configuration (flash layout, slot sizes)
3. Memory map with MPU regions
4. Pin assignments for detected peripherals
5. Recommended RTOS and rationale

**This is manual** — you paste the prompt into ChatGPT, Claude, or a local LLM. The LLM response is not automatically consumed by ebuild.

---

## Remaining Gaps (for future development)

| Feature | Status | Description |
|---------|--------|-------------|
| **Altium/OrCAD importers** | ❌ Not implemented | Binary formats — customers should export BOM as CSV |
| **PDF datasheet parser** | ❌ Not implemented | Would need OCR + table extraction |
| **KiCad hierarchical sheets** | ⚠️ Partial | Top-level sheet parsed, sub-sheets not followed |
| **KiCad PCB layout** | ❌ Not implemented | Use `.kicad_sch` instead |

### Customer Prerequisites

To use ebuild AI analysis, customers should provide **one of**:

| Input Format | How to Provide | Quality |
|-------------|---------------|---------|
| **Text description** | `ebuild analyze "STM32H7 with UART SPI CAN WiFi BLE"` | Good |
| **YAML board file** | `ebuild analyze board.yaml` | Good |
| **KiCad schematic** | `ebuild analyze design.kicad_sch` | Best |
| **Eagle schematic** | `ebuild analyze design.sch` | Best |
| **BOM CSV** | `ebuild analyze bom.csv` | Good (with component DB) |
| **Any text file** | `ebuild analyze spec.txt` | Moderate |

For **Altium/OrCAD** users: export BOM as CSV first, then use the BOM input path.

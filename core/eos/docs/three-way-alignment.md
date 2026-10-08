# Three-Way Alignment Audit: eos ↔ eboot ↔ ebuild

This document tracks alignment between all three EoS components to ensure they reference each other correctly.

---

## Alignment Status: ⚠️ NOT ALIGNED — the inventories disagree and nothing cross-checks them

Measured on 2026-09-14 against origin/master of eos, eBoot and ebuild (eos `9ed6831`, eBoot `221325c`, ebuild `76970c9`). Every number below comes from the commands under "How this was measured"; the previous banner and its counts (25 / 25 / 41 / 24 / 33 / 39 / 5) did not reproduce.

| Dimension | eos | eboot | ebuild | Status |
|-----------|-----|-------|--------|--------|
| Board definitions | 84 `boards/*.yaml` (89 entries in `boards/`; the other 5 are `lm3s6965evb.ld`, `startup_stm32f407.S`, `stm32f407vg.ld`, `stm32f407_discovery/`, `validation/`) | 83 `boards/*/` directories, 83 `eboot_add_board()` calls in `CMakeLists.txt`, 83 `boards/*/board_*.h` | `ebuild/sdk_generator.py`: `TARGET_ARCH` 14, `EBOOT_BOARD` 14, `MCU_TO_EBOOT_BOARD` 136 keys (56 distinct eboot dirs); `ebuild/eos_ai/eos_project_generator.py`: `EOS_BOARD_MAP` 116 keys (81 distinct eos YAMLs) | ⚠️ 84 / 83 / 14+136 are differently-keyed inventories of different sizes and no tool compares them. Every `MCU_TO_EBOOT_BOARD` value is an eboot dir (56/56) but 27 eboot dirs are never targeted; every `EOS_BOARD_MAP` value is an eos YAML (81/81) but `hiletgo-esp-wroom-32.yaml`, `qemu-arm64.yaml` and `tms570.yaml` are never mapped; only 7 eos YAML stems share a name with an eboot dir. |
| Product profiles | 48 `products/*.h`; 42 `#if`/`#elif defined(EOS_PRODUCT_*)` branches in `include/eos/eos_config.h` | — | `PRODUCT_MAP` 41 keys in `eos_project_generator.py` | ⚠️ 48 / 42 / 41. All 41 `PRODUCT_MAP` keys have a header and a config branch. `cast_device`, `desktop`, `home_camera`, `iptv_stb`, `smart_speaker`, `tv_os` have a header but neither a config branch nor a `PRODUCT_MAP` entry; `vbox_test` has a header and a config branch but no `PRODUCT_MAP` entry. |
| Platform enum | — | 24 `eos_platform_t` enumerators in `include/eos_hal.h` | `MCU_DATABASE` 171 keys in `eos_hw_analyzer.py`, using 52 distinct `arch` strings | ⚠️ The 24 reproduces. `MCU_DATABASE` describes MCUs by `arch` strings (`arm`, `mips64`, `sh`, …) that share no vocabulary with the enumerators, and nothing maps one onto the other. |
| Peripheral keywords | 33 peripheral families with an `eos_<family>_init()`: 5 in `hal/include/eos/hal.h`, 28 in `hal/include/eos/hal_extended.h` | — | `PERIPHERAL_KEYWORDS` 46 keywords mapping to 24 distinct types in `eos_hw_analyzer.py`; `ComponentDB` 114 parts in `component_db.py` (its docstring says 200+) | ⚠️ 33 and 24 reproduce; 200+ does not (114). Only 21 of the 24 types are HAL family names: `ethernet`, `gps`, `watchdog` are spelled `eth`, `gnss`, `wdt` in the HAL, and `cellular`, `flash`, `gpu`, `haptic`, `hdmi`, `ir`, `pcie`, `radar`, `touch` have no keyword at all. |
| Multicore support | `kernel/include/eos/multicore.h` (38 declarations: `eos_core_*`, `eos_spin_*`, `eos_ipi_*`, `eos_rproc_*`, `eos_shmem_*`, …) | `include/eos_multicore.h` (12 `eos_multicore_*` declarations) | `MULTICORE_MCUS` 13 names in `eos_project_generator.py` | ⚠️ All three exist, and that is all that was checked: the two headers are different APIs, and nothing compares either of them to `MULTICORE_MCUS`. |
| Config generation | 34 `#define EOS_ENABLE_*` in `include/eos/eos_config.h` | `eboot_flash_layout.h` is not a file in eBoot (0 tracked files); it is generated output that eBoot only documents (`configs/README.md`, `docs/quickstart.md`, `docs/book/book.md`) | `EosConfigGenerator.generate_eos_config_h()` writes `eos_product_config.h`; `EosBootIntegrator.generate_from_boot_yaml()` writes `eboot_flash_layout.h` | ⚠️ 39 did not reproduce (34), and "`EosConfigGenerator` produces both" was wrong: two classes, two files. Across `ebuild/**/*.py` (`eos_hw_analyzer.py` 24, `eos_project_generator.py` 24, `component_db.py` 23; 29 distinct) ebuild names 29 `EOS_ENABLE_*` flags; 24 are defined in `eos_config.h`, `EOS_ENABLE_GPIO`/`I2C`/`SPI`/`TIMER`/`UART` are defined nowhere in eos, and 10 `eos_config.h` flags (`EOS_ENABLE_DISPLAY_DRV`, `EOS_ENABLE_ETHERNET_DRV`, `EOS_ENABLE_GPU`, `EOS_ENABLE_HDMI`, `EOS_ENABLE_MULTICORE`, `EOS_ENABLE_NET`, `EOS_ENABLE_PCIE`, `EOS_ENABLE_PCIE_DRV`, `EOS_ENABLE_SDIO`, `EOS_ENABLE_USB_HOST`) are never named by ebuild. |
| Templates | — | — | 6 directories in `templates/` at the ebuild repo root (`bare-metal`, `ble-sensor`, `linux-app`, `rtos-app`, `safety-critical`, `secure-boot`); `ebuild/templates/` does not exist | ⚠️ "5 in `ebuild/templates/`" did not reproduce: 6, at a different path. eos names four of them by their `ebuild new --template` spelling (`bare-metal` in `GETTING_STARTED.md` and `docs/quickstart-host.md`, `ble-sensor` in `docs/quickstart-nrf52.md`, `linux-app` in `docs/quickstart-rpi4.md`); all four exist in ebuild's `templates/`. eBoot names none. Nothing checks that a documented template name exists. |
| CLI commands | cmake build (`CMakeLists.txt`) | cmake build (`CMakeLists.txt`) | `new`, `build`, `analyze`, `generate-project` are `@cli.command` functions in `ebuild/cli/commands.py` (23 `@cli.command` entries plus the `repos` group with 6 subcommands) | ✅ The four named subcommands exist by name. That is a presence check on ebuild alone, not an inventory comparison. |

---

## How this was measured

Run from a directory holding sibling checkouts `eos/`, `eBoot/` and `ebuild/` with `origin/master` fetched (`git -C <repo> fetch origin`). Every command reads `origin/master`, not the working tree, so it gives the same answer whatever is checked out.

```bash
git -C eos ls-tree --name-only origin/master boards/ | wc -l                                  # 89
git -C eos ls-tree --name-only origin/master boards/ | grep -c '\.yaml$'                      # 84
git -C eos ls-tree --name-only origin/master boards/ | grep -v '\.yaml$'                      # the other 5
git -C eBoot ls-tree origin/master boards/ | grep -c '^040000'                                # 83
git -C eBoot show origin/master:CMakeLists.txt | grep -c 'eboot_add_board('                   # 83
git -C eBoot ls-tree -r --name-only origin/master boards/ | grep -cE '^boards/[^/]+/board_[^/]+\.h$'   # 83
git -C eos ls-tree --name-only origin/master products/ | grep -c '\.h$'                       # 48
git -C eBoot show origin/master:include/eos_hal.h | awk '/typedef enum/{f=1} f && /^[[:space:]]*EOS_PLATFORM_/{n++} /} eos_platform_t;/{f=0} END{print n}'   # 24
git -C eos show origin/master:include/eos/eos_config.h | grep -cE '^\s*#\s*define\s+EOS_ENABLE_'   # 34
git -C ebuild ls-tree origin/master templates/ | grep -c '^040000'                            # 6
git -C ebuild ls-tree --name-only origin/master ebuild/templates/ | wc -l                     # 0: the path does not exist
git -C ebuild show origin/master:ebuild/eos_ai/component_db.py > /tmp/component_db.py
python3 -c "import importlib.util as u, sys; s=u.spec_from_file_location('component_db', sys.argv[1]); m=u.module_from_spec(s); sys.modules['component_db']=m; s.loader.exec_module(m); print(len(m.ComponentDB()._db))" /tmp/component_db.py   # 114
git -C ebuild show origin/master:ebuild/cli/commands.py | grep -cE '^@cli\.command'           # 23
git -C ebuild show origin/master:ebuild/cli/commands.py | grep -cE '^@repos\.command'         # 6
git -C ebuild show origin/master:ebuild/cli/commands.py | grep -oE '^def (new|build|analyze|generate_project)\('   # all four
git -C eos show origin/master:kernel/include/eos/multicore.h | grep -oE '\beos_[a-z0-9_]+\s*\(' | sort -u | wc -l   # 38
git -C eBoot show origin/master:include/eos_multicore.h | tr -d '\r' | grep -oE '\beos_multicore_[a-z0-9_]+\s*\(' | sort -u | wc -l   # 12
git -C ebuild show origin/master:ebuild/eos_ai/eos_config_generator.py | grep -n 'eos_product_config.h'   # written by generate_eos_config_h()
git -C ebuild show origin/master:ebuild/eos_ai/eos_boot_integrator.py | grep -n 'eboot_flash_layout.h'    # written by generate_from_boot_yaml()
git -C eBoot ls-tree -r --name-only origin/master | grep -c 'eboot_flash_layout\.h'           # 0
git -C eBoot grep -l 'eboot_flash_layout' origin/master -- ':!build_sim'                      # configs/README.md, docs/book/book.md, docs/quickstart.md
```

The dictionary sizes and every set comparison in the table come from this script. It parses the ebuild sources with `ast` instead of grepping them: a grep for `":` counts every quoted key in the file, not the entries of one dict.

```python
import ast, re, subprocess

def show(repo, path):
    return subprocess.run(["git", "-C", repo, "show", f"origin/master:{path}"],
                          check=True, capture_output=True, text=True).stdout

def consts(repo, path, *names):
    out = {}
    for node in ast.walk(ast.parse(show(repo, path))):
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            for t in (node.targets if isinstance(node, ast.Assign) else [node.target]):
                if isinstance(t, ast.Name) and t.id in names:
                    out[t.id] = ast.literal_eval(node.value)
    return out

sdk = consts("ebuild", "ebuild/sdk_generator.py", "TARGET_ARCH", "EBOOT_BOARD", "MCU_TO_EBOOT_BOARD")
gen = consts("ebuild", "ebuild/eos_ai/eos_project_generator.py", "EOS_BOARD_MAP", "PRODUCT_MAP", "MULTICORE_MCUS")
hw = consts("ebuild", "ebuild/eos_ai/eos_hw_analyzer.py", "PERIPHERAL_KEYWORDS", "MCU_DATABASE")
for name, d in {**sdk, **gen, **hw}.items():
    print(name, len(d))
print("PERIPHERAL_KEYWORDS distinct values", len(set(hw["PERIPHERAL_KEYWORDS"].values())))
print("MCU_DATABASE distinct arch", len({v["arch"] for v in hw["MCU_DATABASE"].values()}))

yaml = {l.split("/")[-1] for l in show("eos", "boards/").split() if l.endswith(".yaml")}
dirs = {l.split()[-1].split("/")[-1] for l in subprocess.run(
    ["git", "-C", "eBoot", "ls-tree", "origin/master", "boards/"],
    check=True, capture_output=True, text=True).stdout.splitlines() if l.startswith("040000")}
m2e, ebm = sdk["MCU_TO_EBOOT_BOARD"], gen["EOS_BOARD_MAP"]
print("eos yaml", len(yaml), "| eboot dirs", len(dirs),
      "| yaml stems that are eboot dirs", len({y[:-5] for y in yaml} & dirs))
print("MCU_TO_EBOOT_BOARD distinct values", len(set(m2e.values())),
      "| values that are eboot dirs", len(set(m2e.values()) & dirs),
      "| eboot dirs never targeted", len(dirs - set(m2e.values())))
print("EOS_BOARD_MAP distinct values", len(set(ebm.values())),
      "| values that are eos yaml", len(set(ebm.values()) & yaml),
      "| eos yaml never mapped", sorted(yaml - set(ebm.values())))

prods = {l.split("/")[-1][:-2] for l in show("eos", "products/").split() if l.endswith(".h")}
cfg = show("eos", "include/eos/eos_config.h")
chain = {m.lower() for m in re.findall(r"#\s*(?:el)?if\s+defined\s*\(\s*EOS_PRODUCT_([A-Z0-9_]+)\s*\)", cfg)}
pm = set(gen["PRODUCT_MAP"])
print("products/*.h", len(prods), "| eos_config.h product branches", len(chain), "| PRODUCT_MAP", len(pm))
print("headers without PRODUCT_MAP entry", sorted(prods - pm))
print("headers without config branch", sorted(prods - chain), "| PRODUCT_MAP keys without header", sorted(pm - prods))

enables = set(re.findall(r"^\s*#\s*define\s+(EOS_ENABLE_[A-Z0-9_]+)", cfg, re.M))
py_files = [l for l in subprocess.run(["git", "-C", "ebuild", "ls-tree", "-r", "--name-only",
                                        "origin/master", "ebuild/"], capture_output=True,
                                       text=True, check=True).stdout.split() if l.endswith(".py")]
named = set(re.findall(r"EOS_ENABLE_[A-Z0-9_]+", "".join(show("ebuild", f) for f in py_files)))
print("EOS_ENABLE_* defines", len(enables), "| named in ebuild/**/*.py", len(named), "| common", len(enables & named),
      "| ebuild-only", sorted(named - enables), "| eos-only", sorted(enables - named))

fam = set()
for h in ("hal/include/eos/hal.h", "hal/include/eos/hal_extended.h"):
    fam |= set(re.findall(r"\beos_([a-z0-9]+)_init\s*\(", show("eos", h))) - {"hal"}
kw = set(hw["PERIPHERAL_KEYWORDS"].values())
print("HAL init families", len(fam), "| keyword types that are HAL families", len(kw & fam),
      "| keyword types that are not", sorted(kw - fam), "| HAL families with no keyword", sorted(fam - kw))
```

Its output on 2026-09-14:

```
MCU_TO_EBOOT_BOARD 136
TARGET_ARCH 14
EBOOT_BOARD 14
MULTICORE_MCUS 13
PRODUCT_MAP 41
EOS_BOARD_MAP 116
MCU_DATABASE 171
PERIPHERAL_KEYWORDS 46
PERIPHERAL_KEYWORDS distinct values 24
MCU_DATABASE distinct arch 52
eos yaml 84 | eboot dirs 83 | yaml stems that are eboot dirs 7
MCU_TO_EBOOT_BOARD distinct values 56 | values that are eboot dirs 56 | eboot dirs never targeted 27
EOS_BOARD_MAP distinct values 81 | values that are eos yaml 81 | eos yaml never mapped ['hiletgo-esp-wroom-32.yaml', 'qemu-arm64.yaml', 'tms570.yaml']
products/*.h 48 | eos_config.h product branches 42 | PRODUCT_MAP 41
headers without PRODUCT_MAP entry ['cast_device', 'desktop', 'home_camera', 'iptv_stb', 'smart_speaker', 'tv_os', 'vbox_test']
headers without config branch ['cast_device', 'desktop', 'home_camera', 'iptv_stb', 'smart_speaker', 'tv_os'] | PRODUCT_MAP keys without header []
EOS_ENABLE_* defines 34 | named in ebuild/**/*.py 29 | common 24 | ebuild-only ['EOS_ENABLE_GPIO', 'EOS_ENABLE_I2C', 'EOS_ENABLE_SPI', 'EOS_ENABLE_TIMER', 'EOS_ENABLE_UART'] | eos-only ['EOS_ENABLE_DISPLAY_DRV', 'EOS_ENABLE_ETHERNET_DRV', 'EOS_ENABLE_GPU', 'EOS_ENABLE_HDMI', 'EOS_ENABLE_MULTICORE', 'EOS_ENABLE_NET', 'EOS_ENABLE_PCIE', 'EOS_ENABLE_PCIE_DRV', 'EOS_ENABLE_SDIO', 'EOS_ENABLE_USB_HOST']
HAL init families 33 | keyword types that are HAL families 21 | keyword types that are not ['ethernet', 'gps', 'watchdog'] | HAL families with no keyword ['cellular', 'eth', 'flash', 'gnss', 'gpu', 'haptic', 'hdmi', 'ir', 'pcie', 'radar', 'touch', 'wdt']
```

---

## Board-Level Alignment (25 boards)

> Kept from the original audit as a 25-board subset; the full inventories are 84 / 83 / 136 / 116 (status table above). On 2026-09-14 all 25 YAMLs and all 25 eboot directories still exist. The two ebuild columns are shorthand: in 9 rows (`mips`, `powerpc`, `m68k`, `sh4`, `frv`, `h8300`, `mn103`, `strongarm`, `xscale`) the name left of the arrow is not a literal key in at least one of the two maps, which are keyed by MCU part name or name prefix (`mips32`, `pic32`, `jz4740` → `mips`; `mpc`, `p10`, `ppc` → `generic-powerpc.yaml`); the target right of the arrow does exist in every row.

| MCU | eos board YAML | eboot board port | ebuild MCU_TO_EBOOT_BOARD | ebuild EOS_BOARD_MAP |
|-----|---------------|-----------------|--------------------------|---------------------|
| nRF52840 | `nrf52840.yaml` ✅ | `nrf52/` ✅ | `nrf52→nrf52` ✅ | `nrf52→nrf52840.yaml` ✅ |
| STM32F4 | `stm32f4.yaml` ✅ | `stm32f4/` ✅ | `stm32f4→stm32f4` ✅ | `stm32f4→stm32f4.yaml` ✅ |
| STM32H7 | `stm32h743.yaml` ✅ | `stm32h7/` ✅ | `stm32h7→stm32h7` ✅ | `stm32h7→stm32h743.yaml` ✅ |
| SAMD51 | `samd51.yaml` ✅ | `samd51/` ✅ | `samd51→samd51` ✅ | `samd51→samd51.yaml` ✅ |
| STM32MP1 | `stm32mp1.yaml` ✅ | `stm32mp1/` ✅ | `stm32mp1→stm32mp1` ✅ | `stm32mp1→stm32mp1.yaml` ✅ |
| RPi4 | `raspberrypi4.yaml` ✅ | `rpi4/` ✅ | `rpi4→rpi4` ✅ | `rpi4→raspberrypi4.yaml` ✅ |
| i.MX8M | `imx8m.yaml` ✅ | `imx8m/` ✅ | `imx8m→imx8m` ✅ | `imx8→imx8m.yaml` ✅ |
| AM64x | `am64x.yaml` ✅ | `am64x/` ✅ | `am64x→am64x` ✅ | `am64→am64x.yaml` ✅ |
| QEMU ARM64 | `qemu-arm64.yaml` ✅ | `qemu_arm64/` ✅ | `qemu_arm64→qemu_arm64` ✅ | — (QEMU only) |
| RISC-V 64 | `generic-riscv64.yaml` ✅ | `riscv64_virt/` ✅ | `riscv64_virt→riscv64_virt` ✅ | `riscv→generic-riscv64.yaml` ✅ |
| SiFive U74 | `sifive_u.yaml` ✅ | `sifive_u/` ✅ | `sifive_u→sifive_u` ✅ | `sifive→sifive_u.yaml` ✅ |
| ESP32 | `esp32.yaml` ✅ | `esp32/` ✅ | `esp32→esp32` ✅ | `esp32→esp32.yaml` ✅ |
| x86 | `generic-x86.yaml` ✅ | `x86/` ✅ | — | `x86→generic-x86_64.yaml` ✅ |
| x86_64 | `generic-x86_64.yaml` ✅ | `x86_64_efi/` ✅ | `x86_64_efi→x86_64_efi` ✅ | `x86_64→generic-x86_64.yaml` ✅ |
| MIPS | `generic-mips.yaml` ✅ | `mips/` ✅ | `mips→mips` ✅ | `mips→generic-mips.yaml` ✅ |
| PowerPC | `generic-powerpc.yaml` ✅ | `powerpc/` ✅ | `powerpc→powerpc` ✅ | `powerpc→generic-powerpc.yaml` ✅ |
| SPARC | `generic-sparc.yaml` ✅ | `sparc/` ✅ | `sparc→sparc` ✅ | `sparc→generic-sparc.yaml` ✅ |
| M68K | `generic-m68k.yaml` ✅ | `m68k/` ✅ | `m68k→m68k` ✅ | `m68k→generic-m68k.yaml` ✅ |
| SH4 | `generic-sh.yaml` ✅ | `sh4/` ✅ | `sh4→sh4` ✅ | `sh4→generic-sh.yaml` ✅ |
| V850 | `generic-v850.yaml` ✅ | `v850/` ✅ | `v850→v850` ✅ | `v850→generic-v850.yaml` ✅ |
| FR-V | `generic-frv.yaml` ✅ | `frv/` ✅ | `frv→frv` ✅ | `frv→generic-frv.yaml` ✅ |
| H8/300 | `generic-h8300.yaml` ✅ | `h8300/` ✅ | `h8300→h8300` ✅ | `h8300→generic-h8300.yaml` ✅ |
| MN103 | `generic-mn103.yaml` ✅ | `mn103/` ✅ | `mn103→mn103` ✅ | `mn103→generic-mn103.yaml` ✅ |
| StrongARM | `generic-strongarm.yaml` ✅ | `strongarm/` ✅ | `strongarm→strongarm` ✅ | `strongarm→generic-strongarm.yaml` ✅ |
| XScale | `generic-xscale.yaml` ✅ | `xscale/` ✅ | `xscale→xscale` ✅ | `xscale→generic-xscale.yaml` ✅ |

---

## Product Profile Alignment (41 profiles)

> Kept from the original audit. On 2026-09-14 all 41 rows still hold, but `products/` has 48 headers; the 7 with no `PRODUCT_MAP` entry are listed in the status table.

| eos Profile (`products/*.h`) | In `eos_config.h` #elif chain | In ebuild `PRODUCT_MAP` |
|-----|------|------|
| `adapter` | ✅ | ✅ |
| `aerospace` | ✅ | ✅ |
| `ai_edge` | ✅ | ✅ |
| `automotive` | ✅ | ✅ |
| `autonomous` | ✅ | ✅ |
| `banking` | ✅ | ✅ |
| `cockpit` | ✅ | ✅ |
| `computer` | ✅ | ✅ |
| `crypto_hw` | ✅ | ✅ |
| `diagnostic` | ✅ | ✅ |
| `drone` | ✅ | ✅ |
| `ev` | ✅ | ✅ |
| `fitness` | ✅ | ✅ |
| `gaming` | ✅ | ✅ |
| `gateway` | ✅ | ✅ |
| `ground_control` | ✅ | ✅ |
| `hmi` | ✅ | ✅ |
| `industrial` | ✅ | ✅ |
| `infotainment` | ✅ | ✅ |
| `iot` | ✅ | ✅ |
| `medical` | ✅ | ✅ |
| `mobile` | ✅ | ✅ |
| `plc` | ✅ | ✅ |
| `pos` | ✅ | ✅ |
| `printer` | ✅ | ✅ |
| `robot` | ✅ | ✅ |
| `router` | ✅ | ✅ |
| `satellite` | ✅ | ✅ |
| `security_cam` | ✅ | ✅ |
| `server` | ✅ | ✅ |
| `smart_home` | ✅ | ✅ |
| `smart_tv` | ✅ | ✅ |
| `space_comm` | ✅ | ✅ |
| `telecom` | ✅ | ✅ |
| `telemedicine` | ✅ | ✅ |
| `thermostat` | ✅ | ✅ |
| `vacuum` | ✅ | ✅ |
| `voice` | ✅ | ✅ |
| `watch` | ✅ | ✅ |
| `wearable` | ✅ | ✅ |
| `xr_headset` | ✅ | ✅ |

**41/41 profiles aligned across eos and ebuild.**

---

## Data Flow Alignment

```
Customer Input
      │
      ▼
┌──────────────────────────────────────────────────────────────┐
│  ebuild (build system + AI)                                  │
│                                                              │
│  1. EosHardwareAnalyzer                                     │
│     MCU_DATABASE (100+ MCUs) ──► HardwareProfile            │
│     PERIPHERAL_KEYWORDS (24) ──► peripherals[]              │
│     ComponentDB (200+ parts) ──► I2C addr, bus, vendor      │
│     KiCadParser / EagleParser ──► net tracing               │
│     LLMClient (optional) ──► deep analysis                  │
│                                                              │
│  2. EosProjectGenerator                                     │
│     MCU_TO_EBOOT_BOARD ──────────────────► eboot board dir  │
│     EOS_BOARD_MAP ──────────────────────► eos board YAML    │
│     PRODUCT_MAP (41 entries) ──────────► eos product .h     │
│     MULTICORE_MCUS ─────────────────────► multicore config  │
│                                                              │
│  3. EosConfigGenerator                                      │
│     generate_board_yaml() ──────────────► eos board.yaml    │
│     generate_boot_yaml() ───────────────► eboot boot.yaml   │
│     generate_build_yaml() ──────────────► ebuild build.yaml │
│     generate_eos_config_h() ────────────► eos_config.h      │
│                                                              │
│  4. EosBootIntegrator                                       │
│     generate_from_boot_yaml() ──────────► eboot_flash_layout.h │
└──────────────────────────────────────────────────────────────┘
      │                    │                    │
      ▼                    ▼                    ▼
┌──────────┐        ┌──────────┐        ┌──────────┐
│   eos    │        │  eboot   │        │  output  │
│          │        │          │        │          │
│ board.yaml│       │ boot.yaml│        │ build.yaml│
│ config.h  │       │ layout.h │        │          │
│ product.h │       │ board/   │        │          │
│ hal apis  │       │ hal ops  │        │          │
└──────────┘        └──────────┘        └──────────┘
```

---

## Verification Checklist

To verify alignment is maintained after any change:

```bash
# 1. Count eos boards
ls eos/boards/*.yaml | wc -l           # 84 on 2026-09-14

# 2. Count eboot boards
ls eboot/boards/*/board_*.h | wc -l    # 83 on 2026-09-14

# 3. Count eos product profiles
ls eos/products/*.h | wc -l            # 48 on 2026-09-14

# 4. Count eos_config.h #elif entries
grep -c "EOS_PRODUCT_" eos/include/eos/eos_config.h  # 42 on 2026-09-14

# 5. Count ebuild PRODUCT_MAP entries
grep -c '":' ebuild/ebuild/eos_ai/eos_project_generator.py | head -1   # counts every quoted key in the file; use the ast script above (41)

# 6. Count platform enum entries
grep -c "EOS_PLATFORM_" eboot/include/eos_hal.h      # 24 on 2026-09-14

# 7. Run ebuild test
cd ebuild && python test_full_pipeline.py            # test_full_pipeline.py does not exist on ebuild origin/master (2026-09-14)
```

---

## Build System Alignment

> Kept from the original audit; the counts in this table are the original audit's, and the status table at the top supersedes them. On 2026-09-14 eboot's `CMakeLists.txt` has 86 `EBLDR_BOARD STREQUAL "<board>"` branches naming 83 distinct boards (the sentinel `"none"` appears three times; `grep -c 'EBLDR_BOARD STREQUAL' CMakeLists.txt` → 86, distinct quoted literals → 84 including `"none"`), not 25, and eos's `EOS_PRODUCT` is a free-form cache string whose accepted values are listed in its help text, not enumerated in CMake.

### CMake Variables Cross-Reference

| Variable | eos `CMakeLists.txt` | eboot `CMakeLists.txt` | ebuild CLI |
|----------|---------------------|----------------------|-----------|
| Product selection | `EOS_PRODUCT` (41 values) | — | `--product` flag in `generate-project` |
| Board selection | — | `EBLDR_BOARD` (25 values) | `--board` flag in `new` command |
| Toolchain | `CMAKE_TOOLCHAIN_FILE` | `CMAKE_TOOLCHAIN_FILE` | `--toolchain` in build.yaml |
| Test builds | `EOS_BUILD_TESTS=ON` | `EBLDR_BUILD_TESTS=ON` | `pytest tests/` |
| Platform | `EOS_PLATFORM` (linux/rtos) | — | auto-detected from board |
| Cross compile | `CMAKE_CROSSCOMPILING` | `CMAKE_CROSSCOMPILING` | auto from toolchain |

### Build Commands — Complete Flow

```bash
# Step 1: Install ebuild
cd EoS/ebuild && pip install -e .

# Step 2: Generate configs (ebuild → eos + eboot)
ebuild analyze "nRF52840 BLE sensor with I2C SPI"
# Outputs: board.yaml, boot.yaml, eos_product_config.h, eboot_flash_layout.h

# Step 3: Build eos (uses eos CMakeLists.txt)
cd EoS/eos
cmake -B build -DEOS_PRODUCT=iot
cmake --build build
# Outputs: libeos_hal.a, libeos_kernel.a, libeos_*.a

# Step 4: Build eboot (uses eboot CMakeLists.txt)
cd EoS/eboot
cmake -B build -DEBLDR_BOARD=nrf52 -DCMAKE_BUILD_TYPE=Debug
cmake --build build
# Outputs: libeboot_hal.a, libeboot_core.a, ebldr_stage0.bin, eboot_firmware.bin

# Step 5: Sign and flash (uses eboot tools)
cd eBoot/tools
python3 sign_image.py --key key.pem --input ../../eos/build/app.bin --output signed.bin
```

### eboot CMakeLists.txt Board Coverage (25/25)

> Kept from the original audit as a 25-board subset; the full eBoot inventory is 83 board directories (status table above), and 27 of them are never targeted by `MCU_TO_EBOOT_BOARD`. The 25/25 below is true of these 25 rows only.

| Board | In `if/elseif` chain | In FATAL_ERROR help string |
|-------|---------------------|---------------------------|
| stm32f4 | ✅ | ✅ |
| stm32h7 | ✅ | ✅ |
| nrf52 | ✅ | ✅ |
| samd51 | ✅ | ✅ |
| rpi4 | ✅ | ✅ |
| imx8m | ✅ | ✅ |
| am64x | ✅ | ✅ |
| stm32mp1 | ✅ | ✅ |
| qemu_arm64 | ✅ | ✅ |
| riscv64_virt | ✅ | ✅ |
| sifive_u | ✅ | ✅ |
| esp32 | ✅ | ✅ |
| x86 | ✅ | ✅ |
| x86_64_efi | ✅ | ✅ |
| mips | ✅ | ✅ |
| powerpc | ✅ | ✅ |
| sparc | ✅ | ✅ |
| m68k | ✅ | ✅ |
| sh4 | ✅ | ✅ |
| v850 | ✅ | ✅ |
| frv | ✅ | ✅ |
| h8300 | ✅ | ✅ |
| mn103 | ✅ | ✅ |
| strongarm | ✅ | ✅ |
| xscale | ✅ | ✅ |

---

## Documentation Alignment

### Which docs reference which repos

| Document | References eos | References eboot | References ebuild |
|----------|---------------|-----------------|-------------------|
| `EoS/README.md` | ✅ structure, examples, API | ✅ bootloader, stages | ✅ CLI, AI, templates |
| `GETTING_STARTED.md` | ✅ build steps, examples | ✅ secure boot section | ✅ new command, analyze |
| `docs/integration-guide.md` | ✅ standalone build | ✅ flash layout, signing | ✅ generate-project |
| `eos/README.md` | ✅ full API, profiles | ✅ related project link | ✅ related project link |
| `eboot/README.md` | ✅ related project link | ✅ full boot API | ✅ related project link |
| `ebuild/README.md` | ✅ builds eos | ✅ builds eboot | ✅ full CLI reference |
| `docs/hardware-alignment.md` | ⚠️ 25 of 84 board YAMLs | ⚠️ 25 of 83 board ports | ✅ MCU maps |
| `docs/three-way-alignment.md` | ⚠️ measured 2026-09-14; see the status table | ⚠️ measured 2026-09-14; see the status table | ⚠️ measured 2026-09-14; see the status table |
| `docs/adding-hardware.md` | ✅ HAL backends, profiles | ✅ EBOOT_REGISTER_BOARD | ✅ — |
| `docs/api-release-process.md` | ✅ Doxyfile, headers | ✅ Doxyfile, headers | ✅ CLI versioning |
| `eos/docs/api-reference.md` | ✅ all modules | — | — |
| `eos/docs/quickstart-*.md` (4) | ✅ build examples | ✅ flash commands | ✅ new command |
| `eboot/docs/quickstart.md` | — | ✅ build + flash | ✅ generate-boot |
| `ebuild/docs/eos_ai_guide.md` | ✅ product config | ✅ flash layout | ✅ full pipeline |
| `ebuild/docs/ai-input-formats.md` | ✅ enables flags | ✅ flash layout | ✅ parser capabilities |

### Cross-Linking Verification

All docs that reference another repo include correct relative paths:

| From | Link | Target Exists |
|------|------|--------------|
| `EoS/README.md` | `eos/` | ✅ |
| `EoS/README.md` | `eboot/` | ✅ |
| `EoS/README.md` | `ebuild/` | ✅ |
| `EoS/README.md` | `GETTING_STARTED.md` | ✅ |
| `EoS/README.md` | `docs/integration-guide.md` | ✅ |
| `eos/README.md` | `../GETTING_STARTED.md` | ✅ |
| `eos/README.md` | `../docs/integration-guide.md` | ✅ |
| `eos/README.md` | `docs/api-reference.md` | ✅ |
| `eos/README.md` | `docs/quickstart-*.md` | ✅ (4 files) |
| `eos/README.md` | `docs/troubleshooting.md` | ✅ |
| `eos/README.md` | `docs/choosing-a-product-profile.md` | ✅ |
| `eboot/README.md` | `docs/quickstart.md` | ✅ |
| `eboot/README.md` | `../docs/integration-guide.md` | ✅ |

---

## Coding Convention Alignment

| Convention | eos | eboot | ebuild |
|-----------|-----|-------|--------|
| **Language** | C11 | C11 | Python 3.9+ |
| **Naming** | `eos_module_func()` | `eos_module_func()` | `snake_case` (PEP 8) |
| **Return codes** | 0=OK, negative=error | 0=OK, negative=error | Exceptions |
| **Types** | `stdint.h` (uint8_t, etc.) | `stdint.h` (uint8_t, etc.) | Type hints |
| **Headers** | `#ifndef EOS_*_H` guards | `#ifndef EOS_*_H` guards | — |
| **Docs** | Doxygen (`@brief`, `@param`) | Doxygen (`@brief`, `@param`) | Google docstrings |
| **License** | MIT | MIT | MIT |
| **Build** | CMake ≥ 3.16 | CMake ≥ 3.15 | pip + setuptools |
| **Tests** | CTest | CTest | pytest |

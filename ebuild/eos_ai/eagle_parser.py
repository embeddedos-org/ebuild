# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Eagle Schematic Parser — XML parsing for Autodesk Eagle .sch files.

Parses Eagle schematic XML format to extract:
- Component parts (name, value, package, library)
- Net connections (signals connecting component pads)
- Bus definitions

Usage:
    from ebuild.eos_ai.eagle_parser import EagleParser

    parser = EagleParser()
    result = parser.parse("my_design.sch")
    for comp in result.components:
        print(f"{comp.name}: {comp.value} ({comp.package})")
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass
class EagleComponent:
    """A component instance (part) in the Eagle schematic."""
    name: str
    value: str
    library: str = ""
    deviceset: str = ""
    device: str = ""
    package: str = ""
    attributes: Dict[str, str] = field(default_factory=dict)

    @property
    def is_mcu(self) -> bool:
        combined = f"{self.value} {self.deviceset} {self.device}".lower()
        mcu_indicators = [
            "stm32", "nrf52", "esp32", "samd", "rp2040", "pic32",
            "atmega", "attiny", "msp430", "lpc", "imx",
            "efm32", "cc26", "cc13", "cy8c", "psoc",
        ]
        return any(m in combined for m in mcu_indicators)


@dataclass
class EagleNetPin:
    """A pin reference within a net/signal."""
    part: str
    gate: str = ""
    pin: str = ""


@dataclass
class EagleNet:
    """A named electrical signal in the schematic."""
    name: str
    pins: List[EagleNetPin] = field(default_factory=list)


@dataclass
class EagleParseResult:
    """Complete parse result from an Eagle schematic."""
    components: List[EagleComponent] = field(default_factory=list)
    nets: List[EagleNet] = field(default_factory=list)
    version: str = ""
    errors: List[str] = field(default_factory=list)

    def find_component(self, name: str) -> Optional[EagleComponent]:
        for c in self.components:
            if c.name == name:
                return c
        return None

    def find_mcu(self) -> Optional[EagleComponent]:
        for c in self.components:
            if c.is_mcu:
                return c
        return None

    def get_nets_for_part(self, part_name: str) -> List[EagleNet]:
        result = []
        for net in self.nets:
            for pin in net.pins:
                if pin.part == part_name:
                    result.append(net)
                    break
        return result


class EagleParser:
    """Parser for Autodesk Eagle schematic files (.sch).

    Eagle schematics are XML files with this structure:
        <eagle version="9.6.2">
          <drawing>
            <schematic>
              <libraries>...</libraries>
              <parts>
                <part name="U1" library="..." deviceset="..." device="..." value="STM32F407"/>
              </parts>
              <sheets>
                <sheet>
                  <nets>
                    <net name="SDA">
                      <segment>
                        <pinref part="U1" gate="G$1" pin="PB7"/>
                        <pinref part="U2" gate="A" pin="SDA"/>
                      </segment>
                    </net>
                  </nets>
                </sheet>
              </sheets>
            </schematic>
          </drawing>
        </eagle>
    """

    def parse(self, filepath: str) -> EagleParseResult:
        """Parse an Eagle .sch XML file and return structured data."""
        result = EagleParseResult()
        path = Path(filepath)

        if not path.exists():
            result.errors.append(f"File not found: {filepath}")
            return result

        if path.suffix.lower() not in (".sch", ".eagle"):
            result.errors.append(f"Not an Eagle schematic: {filepath}")
            return result

        try:
            tree = ET.parse(str(path))
        except ET.ParseError as e:
            result.errors.append(f"XML parse error: {e}")
            return result
        except OSError as e:
            result.errors.append(f"Failed to read file: {e}")
            return result

        root = tree.getroot()

        if root.tag != "eagle":
            result.errors.append(f"Not an Eagle file, root tag: {root.tag}")
            return result

        result.version = root.get("version", "")

        drawing = root.find("drawing")
        if drawing is None:
            result.errors.append("No <drawing> element found")
            return result

        schematic = drawing.find("schematic")
        if schematic is None:
            result.errors.append("No <schematic> element found")
            return result

        self._extract_parts(schematic, result)
        self._extract_nets(schematic, result)

        return result

    def _extract_parts(self, schematic: ET.Element, result: EagleParseResult) -> None:
        """Extract component parts from the <parts> section."""
        parts_elem = schematic.find("parts")
        if parts_elem is None:
            return

        for part in parts_elem.findall("part"):
            name = part.get("name", "")
            value = part.get("value", "")
            library = part.get("library", "")
            deviceset = part.get("deviceset", "")
            device = part.get("device", "")

            if not name:
                continue

            comp = EagleComponent(
                name=name,
                value=value or deviceset,
                library=library,
                deviceset=deviceset,
                device=device,
            )

            # Extract attributes
            for attr in part.findall("attribute"):
                attr_name = attr.get("name", "")
                attr_value = attr.get("value", "")
                if attr_name:
                    comp.attributes[attr_name] = attr_value

            result.components.append(comp)

        # Resolve packages from libraries
        self._resolve_packages(schematic, result)

    def _resolve_packages(self, schematic: ET.Element, result: EagleParseResult) -> None:
        """Resolve package/footprint names from library definitions."""
        libraries = schematic.find("libraries")
        if libraries is None:
            return

        package_map: Dict[Tuple[str, str, str], str] = {}

        for lib in libraries.findall("library"):
            lib_name = lib.get("name", "")
            devicesets = lib.find("devicesets")
            if devicesets is None:
                continue

            for ds in devicesets.findall("deviceset"):
                ds_name = ds.get("name", "")
                devices = ds.find("devices") if ds.find("devices") is not None else ds
                for dev in devices.findall("device"):
                    dev_name = dev.get("name", "")
                    dev_package = dev.get("package", "")
                    if dev_package:
                        package_map[(lib_name, ds_name, dev_name)] = dev_package

        for comp in result.components:
            key = (comp.library, comp.deviceset, comp.device)
            if key in package_map:
                comp.package = package_map[key]

    def _extract_nets(self, schematic: ET.Element, result: EagleParseResult) -> None:
        """Extract nets/signals from all sheets."""
        sheets = schematic.find("sheets")
        if sheets is None:
            return

        for sheet in sheets.findall("sheet"):
            nets_elem = sheet.find("nets")
            if nets_elem is None:
                continue

            for net_elem in nets_elem.findall("net"):
                net_name = net_elem.get("name", "")
                if not net_name:
                    continue

                net = EagleNet(name=net_name)

                for segment in net_elem.findall("segment"):
                    for pinref in segment.findall("pinref"):
                        pin = EagleNetPin(
                            part=pinref.get("part", ""),
                            gate=pinref.get("gate", ""),
                            pin=pinref.get("pin", ""),
                        )
                        if pin.part:
                            net.pins.append(pin)

                if net.pins:
                    result.nets.append(net)

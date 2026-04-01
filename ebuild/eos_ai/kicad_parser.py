# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""KiCad Schematic Parser — proper S-expression parsing for .kicad_sch files.

Parses KiCad 6/7/8 schematic files to extract:
- Component symbols (reference, value, footprint, library)
- Net connectivity (which pins connect to which nets)
- Pin assignments (MCU pin → peripheral mapping)
- Wire connections between components

Usage:
    from ebuild.eos_ai.kicad_parser import KiCadParser

    parser = KiCadParser()
    result = parser.parse("my_design.kicad_sch")
    for comp in result.components:
        print(f"{comp.reference}: {comp.value} ({comp.footprint})")
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class KiCadPin:
    """A pin on a component symbol."""
    number: str
    name: str
    net: str = ""
    pin_type: str = ""
    position: Tuple[float, float] = (0.0, 0.0)


@dataclass
class KiCadComponent:
    """A component instance in the schematic."""
    reference: str
    value: str
    footprint: str = ""
    lib_id: str = ""
    position: Tuple[float, float] = (0.0, 0.0)
    pins: List[KiCadPin] = field(default_factory=list)
    properties: Dict[str, str] = field(default_factory=dict)

    @property
    def is_mcu(self) -> bool:
        val = self.value.lower()
        mcu_indicators = [
            "stm32", "nrf52", "esp32", "samd", "rp2040", "pic32",
            "atmega", "attiny", "msp430", "lpc", "imx", "sam",
            "efm32", "cc26", "cc13", "cy8c", "psoc",
        ]
        return any(m in val for m in mcu_indicators)


@dataclass
class KiCadNet:
    """A named electrical net connecting component pins."""
    name: str
    pins: List[Tuple[str, str]] = field(default_factory=list)


@dataclass
class KiCadWire:
    """A wire segment in the schematic."""
    start: Tuple[float, float]
    end: Tuple[float, float]


@dataclass
class KiCadParseResult:
    """Complete parse result from a KiCad schematic."""
    components: List[KiCadComponent] = field(default_factory=list)
    nets: List[KiCadNet] = field(default_factory=list)
    wires: List[KiCadWire] = field(default_factory=list)
    version: str = ""
    title: str = ""
    errors: List[str] = field(default_factory=list)

    def find_component(self, reference: str) -> Optional[KiCadComponent]:
        for c in self.components:
            if c.reference == reference:
                return c
        return None

    def find_mcu(self) -> Optional[KiCadComponent]:
        for c in self.components:
            if c.is_mcu:
                return c
        return None

    def get_nets_for_component(self, reference: str) -> List[KiCadNet]:
        result = []
        for net in self.nets:
            for ref, _ in net.pins:
                if ref == reference:
                    result.append(net)
                    break
        return result


class SExprParser:
    """Minimal S-expression parser for KiCad file format.

    KiCad files use a Lisp-like S-expression syntax:
        (kicad_sch (version 20230121) (generator eeschema)
          (symbol (lib_id "Device:R") (at 100 50 0)
            (property "Reference" "R1" ...)
          )
        )
    """

    def __init__(self, text: str):
        self._text = text
        self._pos = 0
        self._len = len(text)

    def parse(self) -> Any:
        self._skip_whitespace()
        if self._pos >= self._len:
            return None
        return self._parse_element()

    def _parse_element(self) -> Any:
        self._skip_whitespace()
        if self._pos >= self._len:
            return None

        ch = self._text[self._pos]

        if ch == '(':
            return self._parse_list()
        elif ch == '"':
            return self._parse_string()
        else:
            return self._parse_atom()

    def _parse_list(self) -> List[Any]:
        self._pos += 1  # skip '('
        items: List[Any] = []
        while self._pos < self._len:
            self._skip_whitespace()
            if self._pos >= self._len:
                break
            if self._text[self._pos] == ')':
                self._pos += 1
                return items
            items.append(self._parse_element())
        return items

    def _parse_string(self) -> str:
        self._pos += 1  # skip opening '"'
        start = self._pos
        while self._pos < self._len:
            ch = self._text[self._pos]
            if ch == '\\' and self._pos + 1 < self._len:
                self._pos += 2
                continue
            if ch == '"':
                result = self._text[start:self._pos]
                self._pos += 1
                return result
            self._pos += 1
        return self._text[start:]

    def _parse_atom(self) -> str:
        start = self._pos
        while self._pos < self._len:
            ch = self._text[self._pos]
            if ch in ' \t\n\r()':
                break
            self._pos += 1
        return self._text[start:self._pos]

    def _skip_whitespace(self) -> None:
        while self._pos < self._len and self._text[self._pos] in ' \t\n\r':
            self._pos += 1


def _find_nodes(tree: List, tag: str) -> List[List]:
    """Find all child nodes with a given tag in an S-expression tree."""
    results = []
    if not isinstance(tree, list):
        return results
    for item in tree:
        if isinstance(item, list) and len(item) > 0 and item[0] == tag:
            results.append(item)
    return results


def _find_node(tree: List, tag: str) -> Optional[List]:
    nodes = _find_nodes(tree, tag)
    return nodes[0] if nodes else None


def _get_property(node: List, name: str) -> str:
    """Get a property value from a symbol node."""
    for item in node:
        if isinstance(item, list) and len(item) >= 3:
            if item[0] == "property" and item[1] == name:
                return str(item[2])
    return ""


def _get_at(node: List) -> Tuple[float, float]:
    """Extract (x, y) position from an 'at' node."""
    at = _find_node(node, "at")
    if at and len(at) >= 3:
        try:
            return (float(at[1]), float(at[2]))
        except (ValueError, TypeError):
            pass
    return (0.0, 0.0)


class KiCadParser:
    """Parser for KiCad 6/7/8 schematic files (.kicad_sch).

    Extracts components, nets, wires, and pin assignments using
    proper S-expression parsing of the KiCad file format.
    """

    def parse(self, filepath: str) -> KiCadParseResult:
        """Parse a .kicad_sch file and return structured data."""
        result = KiCadParseResult()
        path = Path(filepath)

        if not path.exists():
            result.errors.append(f"File not found: {filepath}")
            return result

        if not path.suffix.lower() == ".kicad_sch":
            result.errors.append(f"Not a KiCad schematic: {filepath}")
            return result

        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as e:
            result.errors.append(f"Failed to read file: {e}")
            return result

        try:
            parser = SExprParser(content)
            tree = parser.parse()
        except Exception as e:
            result.errors.append(f"S-expression parse error: {e}")
            return result

        if not isinstance(tree, list) or not tree:
            result.errors.append("Empty or invalid schematic")
            return result

        if tree[0] != "kicad_sch":
            result.errors.append(f"Not a kicad_sch file, got: {tree[0]}")
            return result

        # Extract version
        ver_node = _find_node(tree, "version")
        if ver_node and len(ver_node) >= 2:
            result.version = str(ver_node[1])

        # Extract title block
        title_block = _find_node(tree, "title_block")
        if title_block:
            title_node = _find_node(title_block, "title")
            if title_node and len(title_node) >= 2:
                result.title = str(title_node[1])

        # Extract symbol instances (components)
        self._extract_symbols(tree, result)

        # Extract wires
        self._extract_wires(tree, result)

        # Build net connectivity from labels and global labels
        self._extract_nets(tree, result)

        return result

    def _extract_symbols(self, tree: List, result: KiCadParseResult) -> None:
        """Extract component symbols from the schematic tree."""
        for item in tree:
            if not isinstance(item, list) or len(item) < 2:
                continue
            if item[0] != "symbol":
                continue

            # Skip library symbol definitions (they have nested 'symbol' with lib_id pattern)
            lib_id_node = _find_node(item, "lib_id")
            if not lib_id_node:
                continue

            lib_id = str(lib_id_node[1]) if len(lib_id_node) >= 2 else ""

            reference = _get_property(item, "Reference")
            value = _get_property(item, "Value")
            footprint = _get_property(item, "Footprint")
            position = _get_at(item)

            if not reference or reference.startswith("#"):
                continue

            comp = KiCadComponent(
                reference=reference,
                value=value,
                footprint=footprint,
                lib_id=lib_id,
                position=position,
            )

            # Extract additional properties
            for prop_node in _find_nodes(item, "property"):
                if len(prop_node) >= 3:
                    pname = str(prop_node[1])
                    pval = str(prop_node[2])
                    if pname not in ("Reference", "Value", "Footprint"):
                        comp.properties[pname] = pval

            # Extract pins
            for pin_node in _find_nodes(item, "pin"):
                if len(pin_node) >= 3:
                    pin = KiCadPin(
                        number=str(pin_node[1]) if len(pin_node) > 1 else "",
                        name=str(pin_node[2]) if len(pin_node) > 2 else "",
                        position=_get_at(pin_node),
                    )
                    comp.pins.append(pin)

            result.components.append(comp)

    def _extract_wires(self, tree: List, result: KiCadParseResult) -> None:
        """Extract wire segments."""
        for item in tree:
            if not isinstance(item, list) or item[0] != "wire":
                continue
            pts = _find_node(item, "pts")
            if pts and len(pts) >= 3:
                xy_nodes = _find_nodes(pts, "xy")
                if len(xy_nodes) >= 2:
                    try:
                        start = (float(xy_nodes[0][1]), float(xy_nodes[0][2]))
                        end = (float(xy_nodes[1][1]), float(xy_nodes[1][2]))
                        result.wires.append(KiCadWire(start=start, end=end))
                    except (ValueError, TypeError, IndexError):
                        pass

    def _extract_nets(self, tree: List, result: KiCadParseResult) -> None:
        """Extract net labels and global labels to build connectivity."""
        net_map: Dict[str, KiCadNet] = {}

        # Find net labels (local)
        for item in tree:
            if not isinstance(item, list):
                continue
            if item[0] in ("label", "global_label", "hierarchical_label"):
                if len(item) >= 2:
                    net_name = str(item[1])
                    if net_name not in net_map:
                        net_map[net_name] = KiCadNet(name=net_name)

        # Match labels to nearby component pins by position proximity
        label_positions: List[Tuple[str, Tuple[float, float]]] = []
        for item in tree:
            if not isinstance(item, list):
                continue
            if item[0] in ("label", "global_label", "hierarchical_label"):
                name = str(item[1]) if len(item) >= 2 else ""
                pos = _get_at(item)
                if name:
                    label_positions.append((name, pos))

        # For each component pin, check if any label is at the same position
        for comp in result.components:
            for pin in comp.pins:
                for label_name, label_pos in label_positions:
                    dx = abs(pin.position[0] - label_pos[0])
                    dy = abs(pin.position[1] - label_pos[1])
                    if dx < 2.0 and dy < 2.0:
                        pin.net = label_name
                        if label_name in net_map:
                            net_map[label_name].pins.append(
                                (comp.reference, pin.number)
                            )

        result.nets = list(net_map.values())

    def infer_peripheral_connections(
        self, result: KiCadParseResult
    ) -> Dict[str, List[str]]:
        """Infer which peripherals connect to which MCU pins based on nets.

        Returns a dict like:
            {"I2C_SDA": ["U1.PB7", "U2.SDA"],
             "SPI_MOSI": ["U1.PA7", "U3.MOSI"]}
        """
        connections: Dict[str, List[str]] = {}
        peripheral_net_patterns = [
            (r"(?i)sda|i2c.*sda", "I2C_SDA"),
            (r"(?i)scl|i2c.*scl", "I2C_SCL"),
            (r"(?i)mosi|spi.*mosi", "SPI_MOSI"),
            (r"(?i)miso|spi.*miso", "SPI_MISO"),
            (r"(?i)sck|sclk|spi.*clk", "SPI_SCK"),
            (r"(?i)(?:uart|usart).*tx", "UART_TX"),
            (r"(?i)(?:uart|usart).*rx", "UART_RX"),
            (r"(?i)can.*h", "CAN_H"),
            (r"(?i)can.*l", "CAN_L"),
        ]

        for net in result.nets:
            for pattern, bus_name in peripheral_net_patterns:
                if re.search(pattern, net.name):
                    pin_strs = [f"{ref}.{pin}" for ref, pin in net.pins]
                    if pin_strs:
                        connections.setdefault(bus_name, []).extend(pin_strs)
                    break

        return connections

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Serial console for the target — step 8 of the MVP golden path.

`ebuild flash` puts an image on real hardware; this is how the developer sees
it run. That is why it talks to a serial port rather than wrapping `ebuild
qemu`, which starts an emulator and cannot observe the board that was just
flashed.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

DEFAULT_BAUD = 115200


class MonitorError(Exception):
    """A monitor session could not be started or could not continue."""


@dataclass
class PortInfo:
    device: str
    description: str = ""

    def __str__(self) -> str:
        return self.device if not self.description else "%s  (%s)" % (
            self.device, self.description)


def _require_pyserial():
    try:
        import serial  # noqa: F401
        from serial.tools import list_ports  # noqa: F401
    except ImportError as exc:
        raise MonitorError(
            "pyserial is not installed. Install it with:\n"
            "    pip install pyserial"
        ) from exc
    import serial
    from serial.tools import list_ports
    return serial, list_ports


def available_ports() -> List[PortInfo]:
    """Serial ports the host can currently see."""
    try:
        _serial, list_ports = _require_pyserial()
    except MonitorError:
        return []
    return [PortInfo(p.device, p.description or "") for p in list_ports.comports()]


def resolve_port(port: Optional[str]) -> str:
    """The port to open, or an error naming what the host can actually see.

    An explicit --port is honoured even when it is not in the enumerated list:
    the enumeration misses some adapters, and refusing a port the developer
    named because we failed to list it would be worse than letting open() say
    so. Auto-selection only happens when exactly one port exists, because
    picking one of several at random is how a monitor ends up silently
    attached to the wrong board.
    """
    if port:
        return port

    ports = available_ports()
    if not ports:
        raise MonitorError(
            "No serial ports found. Connect the board, or name the port "
            "explicitly:\n"
            "    ebuild monitor --port /dev/ttyUSB0")
    if len(ports) > 1:
        listing = "\n".join("    %s" % p for p in ports)
        raise MonitorError(
            "Several serial ports are present; name the one to use with "
            "--port:\n%s" % listing)
    return ports[0].device


def baud_from_config(config_path: str = "build.yaml",
                     default: int = DEFAULT_BAUD) -> int:
    """The board's console baud rate, or the default when nothing sets one.

    Looked for at board.console.baud and then monitor.baud, so a project can
    state it once beside the rest of its board settings instead of passing
    --baud on every invocation.
    """
    path = Path(config_path)
    if not path.is_file():
        return default
    try:
        import yaml
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return default
    if not isinstance(data, dict):
        return default

    for section, key in (("board", "console"), ("monitor", None)):
        node = data.get(section)
        if not isinstance(node, dict):
            continue
        if key:
            node = node.get(key)
            if not isinstance(node, dict):
                continue
        baud = node.get("baud")
        if isinstance(baud, int) and baud > 0:
            return baud
    return default


def monitor(port: Optional[str] = None,
            baud: int = DEFAULT_BAUD,
            timeout: float = 0.1,
            stream=None) -> int:
    """Stream the target's serial output until interrupted.

    Returns the number of bytes forwarded, so a caller can tell a session that
    saw traffic from one that attached to a silent port.
    """
    serial, _list_ports = _require_pyserial()
    stream = stream if stream is not None else sys.stdout
    device = resolve_port(port)

    try:
        conn = serial.Serial(device, baud, timeout=timeout)
    except Exception as exc:
        raise MonitorError("Could not open %s at %d baud: %s" % (
            device, baud, exc)) from exc

    forwarded = 0
    try:
        while True:
            chunk = conn.read(4096)
            if chunk:
                forwarded += len(chunk)
                stream.write(chunk.decode("utf-8", errors="replace"))
                stream.flush()
    except KeyboardInterrupt:
        # Ctrl-C is how a monitor session ends. It is not an error, and it must
        # still close the port — leaving it held makes the next run fail with a
        # busy device that looks like a hardware fault.
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return forwarded

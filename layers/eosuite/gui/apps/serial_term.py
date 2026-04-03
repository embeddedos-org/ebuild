# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""
EoSuite Serial Terminal — Serial port connection dialog.
"""
import sys
import os
import glob
import tkinter as tk
from tkinter import ttk, messagebox


def detect_serial_ports():
    """Auto-detect available serial ports."""
    if sys.platform == "win32":
        ports = []
        for i in range(1, 33):
            port = f"COM{i}"
            try:
                import ctypes
                handle = ctypes.windll.kernel32.CreateFileW(
                    f"\\\\.\\{port}", 0x80000000, 0, None, 3, 0, None)
                if handle != -1:
                    ctypes.windll.kernel32.CloseHandle(handle)
                    ports.append(port)
            except Exception:
                pass
        if not ports:
            ports = [f"COM{i}" for i in range(1, 10)]
        return ports
    else:
        patterns = ["/dev/ttyUSB*", "/dev/ttyACM*", "/dev/ttyS*",
                    "/dev/tty.usbserial*", "/dev/tty.usbmodem*"]
        ports = []
        for pattern in patterns:
            ports.extend(glob.glob(pattern))
        if not ports:
            ports = ["/dev/ttyUSB0", "/dev/ttyS0"]
        return sorted(ports)


BAUD_RATES = ["9600", "19200", "38400", "57600", "115200", "230400", "460800",
              "921600"]


class SerialDialog(tk.Toplevel):
    """Dialog for creating a new serial connection."""

    def __init__(self, parent, app):
        super().__init__(parent)
        self.app = app
        self.title("New Serial Connection")
        self.geometry("400x320")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self._build()

    def _build(self):
        c = self.app.theme.colors
        self.configure(bg=c["bg"])

        main = ttk.Frame(self, padding=20)
        main.pack(fill=tk.BOTH, expand=True)

        ttk.Label(main, text="🔌 New Serial Connection",
                  font=("Segoe UI", 14, "bold")).pack(pady=(0, 16))

        # Port selection
        port_row = ttk.Frame(main)
        port_row.pack(fill=tk.X, pady=4)
        ttk.Label(port_row, text="Port:", width=12).pack(side=tk.LEFT)
        ports = detect_serial_ports()
        self.port_var = tk.StringVar(value=ports[0] if ports else "")
        port_combo = ttk.Combobox(port_row, textvariable=self.port_var,
                                  values=ports)
        port_combo.pack(fill=tk.X, expand=True, side=tk.LEFT)

        # Refresh ports
        ttk.Button(port_row, text="↻", width=3,
                   command=self._refresh_ports).pack(side=tk.RIGHT, padx=(4, 0))

        # Baud rate
        baud_row = ttk.Frame(main)
        baud_row.pack(fill=tk.X, pady=4)
        ttk.Label(baud_row, text="Baud Rate:", width=12).pack(side=tk.LEFT)
        self.baud_var = tk.StringVar(value="115200")
        baud_combo = ttk.Combobox(baud_row, textvariable=self.baud_var,
                                  values=BAUD_RATES)
        baud_combo.pack(fill=tk.X, expand=True, side=tk.LEFT)

        # Data bits
        data_row = ttk.Frame(main)
        data_row.pack(fill=tk.X, pady=4)
        ttk.Label(data_row, text="Data Bits:", width=12).pack(side=tk.LEFT)
        self.data_var = tk.StringVar(value="8")
        ttk.Combobox(data_row, textvariable=self.data_var,
                     values=["5", "6", "7", "8"]).pack(
            fill=tk.X, expand=True, side=tk.LEFT)

        # Parity
        parity_row = ttk.Frame(main)
        parity_row.pack(fill=tk.X, pady=4)
        ttk.Label(parity_row, text="Parity:", width=12).pack(side=tk.LEFT)
        self.parity_var = tk.StringVar(value="None")
        ttk.Combobox(parity_row, textvariable=self.parity_var,
                     values=["None", "Even", "Odd"]).pack(
            fill=tk.X, expand=True, side=tk.LEFT)

        # Stop bits
        stop_row = ttk.Frame(main)
        stop_row.pack(fill=tk.X, pady=4)
        ttk.Label(stop_row, text="Stop Bits:", width=12).pack(side=tk.LEFT)
        self.stop_var = tk.StringVar(value="1")
        ttk.Combobox(stop_row, textvariable=self.stop_var,
                     values=["1", "1.5", "2"]).pack(
            fill=tk.X, expand=True, side=tk.LEFT)

        # Session name
        name_row = ttk.Frame(main)
        name_row.pack(fill=tk.X, pady=4)
        ttk.Label(name_row, text="Name:", width=12).pack(side=tk.LEFT)
        self.name_var = tk.StringVar()
        ttk.Entry(name_row, textvariable=self.name_var).pack(
            fill=tk.X, expand=True, side=tk.LEFT)

        # Buttons
        btn_frame = ttk.Frame(main)
        btn_frame.pack(pady=(16, 0))
        ttk.Button(btn_frame, text="Connect",
                   command=self._connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Save & Connect",
                   command=self._save_and_connect).pack(side=tk.LEFT, padx=4)
        ttk.Button(btn_frame, text="Cancel",
                   command=self.destroy).pack(side=tk.LEFT, padx=4)

    def _refresh_ports(self):
        ports = detect_serial_ports()
        self.port_var.set(ports[0] if ports else "")

    def _build_command(self):
        port = self.port_var.get().strip()
        baud = self.baud_var.get().strip()
        if not port:
            messagebox.showwarning("Missing Port", "Please select a serial port.")
            return None
        # Use system serial tools
        if sys.platform == "win32":
            cmd = f"mode {port} baud={baud} data={self.data_var.get()} parity={self.parity_var.get()[0]} stop={self.stop_var.get()} && type {port}"
        else:
            cmd = f"screen {port} {baud}"
        return cmd

    def _get_name(self):
        name = self.name_var.get().strip()
        if not name:
            name = f"{self.port_var.get()} @ {self.baud_var.get()}"
        return name

    def _get_connection_str(self):
        return f"{self.port_var.get()}:{self.baud_var.get()}"

    def _connect(self):
        cmd = self._build_command()
        if cmd:
            name = self._get_name()
            self.app.connect_session(cmd, name)
            self.destroy()

    def _save_and_connect(self):
        cmd = self._build_command()
        if cmd:
            name = self._get_name()
            try:
                from gui.apps.session_manager import SessionManager
                mgr = SessionManager()
                mgr.add_session(name, "serial", self._get_connection_str())
                self.app.sidebar.add_serial_session(name, cmd)
            except Exception:
                pass
            self.app.connect_session(cmd, name)
            self.destroy()

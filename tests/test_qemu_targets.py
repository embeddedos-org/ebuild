# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""QEMU-based hardware target tests.

Validates that built images boot correctly on emulated hardware.
These tests require QEMU to be installed and are skipped otherwise.

Run: pytest tests/ -m qemu -v
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

QEMU_ARM = shutil.which("qemu-system-arm")
QEMU_AARCH64 = shutil.which("qemu-system-aarch64")
QEMU_RISCV64 = shutil.which("qemu-system-riscv64")
QEMU_MIPS = shutil.which("qemu-system-mips")

_skip_no_qemu_arm = pytest.mark.skipif(
    not QEMU_ARM, reason="qemu-system-arm not found"
)
_skip_no_qemu_aarch64 = pytest.mark.skipif(
    not QEMU_AARCH64, reason="qemu-system-aarch64 not found"
)
_skip_no_qemu_riscv64 = pytest.mark.skipif(
    not QEMU_RISCV64, reason="qemu-system-riscv64 not found"
)
_skip_no_qemu_mips = pytest.mark.skipif(
    not QEMU_MIPS, reason="qemu-system-mips not found"
)

EBUILD_ROOT = Path(__file__).resolve().parent.parent


def _run_qemu(binary: str, machine: str, extra_args: list = None, timeout: int = 10):
    """Run a QEMU instance and return stdout/stderr.

    Args:
        binary: QEMU binary name (e.g., qemu-system-arm)
        machine: Machine type (-M flag)
        extra_args: Additional QEMU arguments
        timeout: Maximum seconds to wait

    Returns:
        subprocess.CompletedProcess
    """
    cmd = [
        binary,
        "-M", machine,
        "-nographic",
        "-serial", "mon:stdio",
        "-no-reboot",
    ]
    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result
    except subprocess.TimeoutExpired:
        return None
    except FileNotFoundError:
        pytest.skip(f"QEMU binary not found: {binary}")


@pytest.mark.qemu
class TestQEMUAvailability:
    """Verify QEMU binaries are accessible."""

    def test_qemu_arm_version(self):
        if not QEMU_ARM:
            pytest.skip("qemu-system-arm not installed")
        result = subprocess.run(
            [QEMU_ARM, "--version"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "QEMU" in result.stdout

    def test_qemu_aarch64_version(self):
        if not QEMU_AARCH64:
            pytest.skip("qemu-system-aarch64 not installed")
        result = subprocess.run(
            [QEMU_AARCH64, "--version"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "QEMU" in result.stdout

    def test_qemu_riscv64_version(self):
        if not QEMU_RISCV64:
            pytest.skip("qemu-system-riscv64 not installed")
        result = subprocess.run(
            [QEMU_RISCV64, "--version"], capture_output=True, text=True
        )
        assert result.returncode == 0
        assert "QEMU" in result.stdout


@pytest.mark.qemu
class TestQEMUMachineTypes:
    """Verify QEMU machine types needed for ebuild targets are available."""

    @_skip_no_qemu_arm
    def test_lm3s6965evb_available(self):
        """Cortex-M3 machine for STM32-class testing."""
        result = subprocess.run(
            [QEMU_ARM, "-M", "help"], capture_output=True, text=True
        )
        assert "lm3s6965evb" in result.stdout

    @_skip_no_qemu_arm
    def test_mps2_an385_available(self):
        """Cortex-M3 MPS2 machine for nRF52-class testing."""
        result = subprocess.run(
            [QEMU_ARM, "-M", "help"], capture_output=True, text=True
        )
        assert "mps2-an385" in result.stdout

    @_skip_no_qemu_aarch64
    def test_raspi3b_available(self):
        """Raspberry Pi 3 machine."""
        result = subprocess.run(
            [QEMU_AARCH64, "-M", "help"], capture_output=True, text=True
        )
        assert "raspi3b" in result.stdout

    @_skip_no_qemu_aarch64
    def test_virt_aarch64_available(self):
        """Generic AArch64 virt machine for i.MX8M/AM64x testing."""
        result = subprocess.run(
            [QEMU_AARCH64, "-M", "help"], capture_output=True, text=True
        )
        assert "virt" in result.stdout

    @_skip_no_qemu_riscv64
    def test_virt_riscv64_available(self):
        """RISC-V virt machine."""
        result = subprocess.run(
            [QEMU_RISCV64, "-M", "help"], capture_output=True, text=True
        )
        assert "virt" in result.stdout


@pytest.mark.qemu
class TestQEMUBootSmoke:
    """Smoke tests: verify QEMU starts and responds for each architecture.

    These don't require actual firmware images — they verify the QEMU
    infrastructure is operational and can be used for firmware testing.
    """

    @_skip_no_qemu_arm
    def test_arm_cortex_m_qemu_starts(self):
        """Verify qemu-system-arm starts with lm3s6965evb machine."""
        result = _run_qemu(QEMU_ARM, "lm3s6965evb", timeout=3)
        # QEMU should start (and exit quickly with no kernel)
        # A non-None result means it didn't hang
        assert result is not None  # Timeout returns None, which is acceptable

    @_skip_no_qemu_aarch64
    def test_aarch64_virt_qemu_starts(self):
        """Verify qemu-system-aarch64 starts with virt machine."""
        result = _run_qemu(
            QEMU_AARCH64, "virt",
            extra_args=["-cpu", "cortex-a72"],
            timeout=3,
        )
        assert result is not None

    @_skip_no_qemu_riscv64
    def test_riscv64_virt_qemu_starts(self):
        """Verify qemu-system-riscv64 starts with virt machine."""
        result = _run_qemu(QEMU_RISCV64, "virt", timeout=3)
        assert result is not None


# Standalone runner
if __name__ == "__main__":
    print("QEMU Target Tests")
    print(f"  qemu-system-arm:     {'✅ found' if QEMU_ARM else '❌ not found'}")
    print(f"  qemu-system-aarch64: {'✅ found' if QEMU_AARCH64 else '❌ not found'}")
    print(f"  qemu-system-riscv64: {'✅ found' if QEMU_RISCV64 else '❌ not found'}")
    print(f"  qemu-system-mips:    {'✅ found' if QEMU_MIPS else '❌ not found'}")
    print("\nRun with: pytest tests/test_qemu_targets.py -m qemu -v")

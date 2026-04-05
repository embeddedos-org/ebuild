# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""EoS Config Validator — validates generated configs against schemas.

Checks board.yaml, boot.yaml, and build.yaml for correctness
before they are consumed by eos or eboot build pipelines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import yaml


@dataclass
class ValidationError:
    file: str
    field: str
    message: str
    severity: str = "error"


@dataclass
class ValidationResult:
    valid: bool = True
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)

    def add_error(self, file: str, fld: str, msg: str):
        self.errors.append(ValidationError(file, fld, msg, "error"))
        self.valid = False

    def add_warning(self, file: str, fld: str, msg: str):
        self.warnings.append(ValidationError(file, fld, msg, "warning"))

    def summary(self) -> str:
        lines = []
        for e in self.errors:
            lines.append(f"  ERROR [{e.file}] {e.field}: {e.message}")
        for w in self.warnings:
            lines.append(f"  WARN  [{w.file}] {w.field}: {w.message}")
        status = "PASS" if self.valid else "FAIL"
        lines.insert(0, f"Validation: {status} ({len(self.errors)} errors, {len(self.warnings)} warnings)")
        return "\n".join(lines)


class EosConfigValidator:
    """Validates generated configs against expected schemas."""

    REQUIRED_BOARD_FIELDS = ["name", "arch"]
    REQUIRED_BOOT_FIELDS = ["board", "flash_size"]
    VALID_ARCHS = ["arm", "arm64", "xtensa", "riscv32", "riscv64", "x86_64",
                   "x86", "mips", "mips64", "m68k", "powerpc", "sh", "sparc", "mipsel"]
    VALID_HASH_ALGOS = ["sha256", "sha512"]
    VALID_SIGN_ALGOS = ["ed25519", "rsa2048", "rsa4096", "ecdsa_p256"]

    def validate_all(self, config_dir: str) -> ValidationResult:
        """Validate all generated configs in a directory."""
        result = ValidationResult()
        config_path = Path(config_dir)

        board_file = config_path / "board.yaml"
        if board_file.exists():
            self._validate_board(board_file, result)
        else:
            result.add_warning("board.yaml", "", "File not found")

        boot_file = config_path / "boot.yaml"
        if boot_file.exists():
            self._validate_boot(boot_file, result)
        else:
            result.add_warning("boot.yaml", "", "File not found")

        build_file = config_path / "build.yaml"
        if build_file.exists():
            self._validate_build(build_file, result)

        return result

    def validate_board(self, path: str) -> ValidationResult:
        result = ValidationResult()
        self._validate_board(Path(path), result)
        return result

    def validate_boot(self, path: str) -> ValidationResult:
        result = ValidationResult()
        self._validate_boot(Path(path), result)
        return result

    def _validate_board(self, path: Path, result: ValidationResult):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as e:
            result.add_error("board.yaml", "", f"Parse error: {e}")
            return

        if not isinstance(data, dict):
            result.add_error("board.yaml", "", "Invalid format: expected YAML mapping")
            return

        board = data.get("board", data)
        if not isinstance(board, dict):
            result.add_error("board.yaml", "board", "Board section must be a mapping")
            return

        if not board.get("name"):
            result.add_error("board.yaml", "name", "Board name is required")
        if not board.get("arch"):
            result.add_error("board.yaml", "arch", "Architecture is required")
        elif board["arch"] not in self.VALID_ARCHS:
            result.add_warning("board.yaml", "arch",
                               f"Unknown arch '{board['arch']}' — valid: {self.VALID_ARCHS}")

        mem = board.get("memory", {})
        flash = mem.get("flash", 0)
        ram = mem.get("ram", 0)
        if flash <= 0:
            result.add_warning("board.yaml", "memory.flash", "Flash size not specified or zero")
        if ram <= 0:
            result.add_warning("board.yaml", "memory.ram", "RAM size not specified or zero")

    def _validate_boot(self, path: Path, result: ValidationResult):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as e:
            result.add_error("boot.yaml", "", f"Parse error: {e}")
            return

        if not isinstance(data, dict):
            result.add_error("boot.yaml", "", "Invalid format: expected YAML mapping")
            return

        boot = data.get("boot", data)
        if not isinstance(boot, dict):
            result.add_error("boot.yaml", "boot", "Boot section must be a mapping")
            return

        if not boot.get("board"):
            result.add_error("boot.yaml", "board", "Board name is required")

        flash_size = boot.get("flash_size", 0)
        if flash_size <= 0:
            result.add_error("boot.yaml", "flash_size", "Flash size must be > 0")

        layout = boot.get("layout", {})
        if not layout.get("slot_a"):
            result.add_error("boot.yaml", "layout.slot_a", "Slot A definition required")
        if not layout.get("slot_b"):
            result.add_warning("boot.yaml", "layout.slot_b", "Slot B not defined — no A/B update support")

        policy = boot.get("policy", {})
        max_att = policy.get("max_boot_attempts", 0)
        if max_att <= 0:
            result.add_warning("boot.yaml", "policy.max_boot_attempts",
                               "max_boot_attempts should be > 0")

        image = boot.get("image", {})
        hash_algo = image.get("hash_algo", "")
        if hash_algo and hash_algo not in self.VALID_HASH_ALGOS:
            result.add_warning("boot.yaml", "image.hash_algo",
                               f"Unknown hash algo '{hash_algo}'")

        sign_algo = image.get("sign_algo", "")
        if sign_algo and sign_algo not in self.VALID_SIGN_ALGOS:
            result.add_warning("boot.yaml", "image.sign_algo",
                               f"Unknown sign algo '{sign_algo}'")

    def _validate_build(self, path: Path, result: ValidationResult):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as e:
            result.add_error("build.yaml", "", f"Parse error: {e}")
            return

        if not isinstance(data, dict):
            result.add_error("build.yaml", "", "Invalid format: expected YAML mapping")
            return

        project = data.get("project", {})
        if not isinstance(project, dict):
            result.add_error("build.yaml", "project", "Project section must be a mapping")
            return

        if not project.get("name"):
            result.add_error("build.yaml", "project.name", "Project name is required")

        targets = data.get("targets", [])
        if not targets:
            result.add_warning("build.yaml", "targets", "No build targets defined")

        toolchain = data.get("toolchain", {})
        if isinstance(toolchain, dict) and not toolchain.get("compiler"):
            result.add_warning("build.yaml", "toolchain.compiler", "Compiler not specified")

# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project
"""EosConfigValidator must report empty YAML keys as validation findings.

A hand-written boot.yaml or board.yaml with a key present but left empty
(``layout:``, ``policy:``, ``image:``, ``memory:``, ``flash_size:``) loads as
None. The validator used ``boot.get("layout", {})`` and ``flash_size <= 0``,
which only default a *missing* key, so it raised AttributeError/TypeError
instead of returning a ValidationResult. ``ebuild generate-boot`` then printed
"Generation failed: 'NoneType' object has no attribute 'get'" instead of the
validation errors that say what to fix.
"""
from ebuild.eos_ai.eos_validator import EosConfigValidator


def test_boot_yaml_with_empty_sections_reports_errors(tmp_path):
    boot = tmp_path / "boot.yaml"
    boot.write_text(
        "boot:\n"
        "  board: demo\n"
        "  flash_size:\n"
        "  layout:\n"
        "  policy:\n"
        "  image:\n",
        encoding="utf-8",
    )

    result = EosConfigValidator().validate_boot(str(boot))

    assert not result.valid
    error_fields = {e.field for e in result.errors}
    assert "flash_size" in error_fields
    assert "layout.slot_a" in error_fields
    warning_fields = {w.field for w in result.warnings}
    assert "policy.max_boot_attempts" in warning_fields


def test_board_yaml_with_empty_memory_reports_warnings(tmp_path):
    board = tmp_path / "board.yaml"
    board.write_text(
        "board:\n"
        "  name: demo\n"
        "  arch: arm\n"
        "  memory:\n",
        encoding="utf-8",
    )

    result = EosConfigValidator().validate_board(str(board))

    assert result.valid
    warning_fields = {w.field for w in result.warnings}
    assert {"memory.flash", "memory.ram"} <= warning_fields


def test_board_yaml_with_empty_flash_and_ram_reports_warnings(tmp_path):
    board = tmp_path / "board.yaml"
    board.write_text(
        "board:\n"
        "  name: demo\n"
        "  arch: arm\n"
        "  memory:\n"
        "    flash:\n"
        "    ram:\n",
        encoding="utf-8",
    )

    result = EosConfigValidator().validate_board(str(board))

    warning_fields = {w.field for w in result.warnings}
    assert {"memory.flash", "memory.ram"} <= warning_fields

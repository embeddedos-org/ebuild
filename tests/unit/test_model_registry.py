# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for `ebuild model` (Track 1 model registry, phase 1).

Round-trip: register -> list -> pin -> show. The registry is project-local
(cwd/.ebuild/models.json); tests isolate the working directory with tmp_path
so they never touch a real project.
"""

import hashlib
import json

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import cli


@pytest.fixture
def project(tmp_path, monkeypatch):
    """An isolated project directory that becomes cwd for the registry."""
    model = tmp_path / "mobilenet.quantized.int8.tflite"
    model.write_bytes(b"\x1c\x00\x00\x00fake-quantized-model-bytes")
    calib = tmp_path / "calib"
    calib.mkdir()
    (calib / "sample.bin").write_bytes(b"\x00" * 16)
    monkeypatch.chdir(tmp_path)
    return tmp_path, model, calib


def invoke(*args):
    return CliRunner().invoke(cli, ["model", *args])


def register_args(model, calib, *extra, **options):
    args = [
        "register",
        "--file",
        str(model),
        "--target",
        options.get("target", "cmsis-nn"),
        "--format",
        options.get("fmt", "int8"),
        "--calibration",
        str(calib),
    ]
    if "name" in options:
        args += ["--name", options["name"]]
    args.extend(extra)
    return args


def registry(path):
    """Read the project-local registry, or None when unwritten."""
    p = path / ".ebuild" / "models.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None


class TestModelGroupRegistered:
    def test_model_is_a_group(self):
        assert "model" in cli.commands

    def test_model_help_lists_subcommands(self):
        result = invoke("--help")
        assert result.exit_code == 0
        for sub in ("register", "list", "pin", "show"):
            assert sub in result.output


class TestRegisterListPinRoundTrip:
    def test_register_writes_entry(self, project):
        proj, model, calib = project
        result = invoke(*register_args(model, calib))
        assert result.exit_code == 0, result.output
        data = registry(proj)
        assert data is not None
        entry = data["mobilenet.quantized.int8"]
        assert entry["name"] == "mobilenet.quantized.int8"
        assert entry["digest"] == hashlib.sha256(model.read_bytes()).hexdigest()
        assert entry["target"] == "cmsis-nn"
        assert entry["format"] == "int8"
        sample_hash = hashlib.sha256(b"\x00" * 16).hexdigest()
        expected_calib = hashlib.sha256(
            b"sample.bin\x00" + sample_hash.encode()
        ).hexdigest()
        assert entry["calibration_hash"] == expected_calib
        assert entry["source_path"] == str(model)
        assert entry["registered_at"].endswith("Z")

    def test_register_custom_name(self, project):
        proj, model, calib = project
        result = invoke(*register_args(model, calib, name="mbnet-v1"))
        assert result.exit_code == 0, result.output
        assert "mbnet-v1" in registry(proj)

    def test_list_shows_registered_model(self, project):
        proj, model, calib = project
        invoke(*register_args(model, calib, name="mbnet"))
        result = invoke("list")
        assert result.exit_code == 0
        assert "mbnet" in result.output
        assert "cmsis-nn" in result.output
        assert "int8" in result.output

    def test_list_empty_registry(self, project):
        result = invoke("list")
        assert result.exit_code == 0
        assert "No models registered" in result.output

    def test_pin_prints_pin_string(self, project):
        proj, model, calib = project
        invoke(*register_args(model, calib, name="mbnet"))
        result = invoke("pin", "--name", "mbnet")
        assert result.exit_code == 0
        digest = registry(proj)["mbnet"]["digest"]
        assert result.output.strip() == f"mbnet@sha256:{digest}"

    def test_pin_unknown_name_fails(self, project):
        result = invoke("pin", "--name", "nope")
        assert result.exit_code != 0

    def test_show_prints_full_entry(self, project):
        proj, model, calib = project
        invoke(*register_args(model, calib, name="mbnet"))
        result = invoke("show", "--name", "mbnet")
        assert result.exit_code == 0
        entry = registry(proj)["mbnet"]
        for key, value in entry.items():
            assert key in result.output
            assert str(value) in result.output

    def test_show_unknown_name_fails(self, project):
        result = invoke("show", "--name", "nope")
        assert result.exit_code != 0


class TestRegisterFailClosed:
    def test_missing_file_refused_with_no_registry_write(self, project):
        proj, model, calib = project
        result = invoke(*register_args(proj / "ghost.tflite", calib))
        assert result.exit_code != 0
        assert registry(proj) is None
        assert not (proj / ".ebuild").exists()

    def test_missing_calibration_is_usage_error(self, project):
        proj, model, calib = project
        result = invoke(
            "register",
            "--file",
            str(model),
            "--target",
            "cmsis-nn",
            "--calibration",
            str(proj / "no-calib"),
        )
        assert result.exit_code == 2
        assert registry(proj) is None

    def test_bad_target_is_usage_error(self, project):
        proj, model, calib = project
        result = invoke(*register_args(model, calib, target="tensorrt"))
        assert result.exit_code == 2
        assert registry(proj) is None

    def test_bad_format_is_usage_error(self, project):
        proj, model, calib = project
        result = invoke(*register_args(model, calib, fmt="fp32"))
        assert result.exit_code == 2
        assert registry(proj) is None


class TestDuplicateNames:
    def test_duplicate_name_refused(self, project):
        proj, model, calib = project
        assert invoke(*register_args(model, calib, name="mbnet")).exit_code == 0
        before = registry(proj)
        result = invoke(*register_args(model, calib, name="mbnet"))
        assert result.exit_code != 0
        assert "--force" in result.output
        assert registry(proj) == before  # entry untouched

    def test_duplicate_name_allowed_with_force(self, project):
        proj, model, calib = project
        assert invoke(*register_args(model, calib, name="mbnet")).exit_code == 0
        result = invoke(*register_args(model, calib, name="mbnet"), "--force")
        assert result.exit_code == 0, result.output
        assert "mbnet" in registry(proj)


class TestDigestIntegrity:
    def test_tampered_file_changes_digest(self, project):
        proj, model, calib = project
        invoke(*register_args(model, calib, name="mbnet"))
        before = registry(proj)["mbnet"]["digest"]
        model.write_bytes(b"\x1c\x00\x00\x00tampered-bytes")
        result = invoke(*register_args(model, calib, name="mbnet"), "--force")
        assert result.exit_code == 0, result.output
        after = registry(proj)["mbnet"]["digest"]
        assert after == hashlib.sha256(model.read_bytes()).hexdigest()
        assert after != before

    def test_calibration_change_changes_calibration_hash(self, project):
        proj, model, calib = project
        invoke(*register_args(model, calib, name="mbnet"))
        before = registry(proj)["mbnet"]["calibration_hash"]
        (calib / "sample.bin").write_bytes(b"\xff" * 16)
        result = invoke(*register_args(model, calib, name="mbnet2"))
        assert result.exit_code == 0, result.output
        assert registry(proj)["mbnet2"]["calibration_hash"] != before

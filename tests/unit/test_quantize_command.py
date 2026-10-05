# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

"""Tests for `ebuild quantize` (Track 1 model-pipeline skeleton).

The CLI contract is settled (see docs/quantize.md); backend kernels are not
implemented yet, so the command must validate everything, print the plan,
and exit 2 rather than silently no-op'ing.
"""

import pytest
from click.testing import CliRunner

from ebuild.cli.commands import cli


@pytest.fixture
def model_files(tmp_path):
    model = tmp_path / "mobilenet.tflite"
    model.write_bytes(b"\x1c\x00\x00\x00TFL3fake-model-bytes")
    calib = tmp_path / "calib"
    calib.mkdir()
    (calib / "sample.bin").write_bytes(b"\x00" * 16)
    return model, calib


def invoke(*args):
    return CliRunner().invoke(cli, ["quantize", *args])


class TestQuantizeRegistered:
    def test_quantize_is_a_command(self):
        assert "quantize" in cli.commands


class TestQuantizeArgs:
    def test_missing_model_is_usage_error(self, model_files):
        _, calib = model_files
        result = invoke("--calibration", str(calib), "--target", "cmsis-nn")
        assert result.exit_code == 2

    def test_missing_target_is_usage_error(self, model_files):
        model, calib = model_files
        result = invoke("--model", str(model), "--calibration", str(calib))
        assert result.exit_code == 2

    def test_bad_target_choice_is_usage_error(self, model_files):
        model, calib = model_files
        result = invoke(
            "--model", str(model),
            "--calibration", str(calib),
            "--target", "tensorrt",
        )
        assert result.exit_code == 2

    def test_unsupported_model_suffix_rejected(self, tmp_path):
        model = tmp_path / "model.pb"
        model.write_bytes(b"fake")
        calib = tmp_path / "calib"
        calib.mkdir()
        result = invoke(
            "--model", str(model),
            "--calibration", str(calib),
            "--target", "cmsis-nn",
        )
        assert result.exit_code == 2
        assert "Unsupported model format" in result.output

    def test_onnx_accepted(self, tmp_path):
        model = tmp_path / "net.onnx"
        model.write_bytes(b"fake-onnx")
        calib = tmp_path / "calib"
        calib.mkdir()
        result = invoke(
            "--model", str(model),
            "--calibration", str(calib),
            "--target", "esp-nn",
        )
        assert result.exit_code == 2  # skeleton: honest not-implemented
        assert "net.onnx" in result.output


class TestQuantizeSkeletonHonesty:
    def test_skeleton_never_silently_noops(self, model_files):
        model, calib = model_files
        result = invoke(
            "--model", str(model),
            "--calibration", str(calib),
            "--target", "cmsis-nn",
        )
        assert result.exit_code == 2
        assert "not yet implemented" in result.output
        assert "nothing was written" in result.output

    def test_validate_hooks_the_harness_stub(self, model_files):
        model, calib = model_files
        result = invoke(
            "--model", str(model),
            "--calibration", str(calib),
            "--target", "esp-nn",
            "--validate",
        )
        assert result.exit_code == 2
        assert "bit-exactness" in result.output

    def test_aie_points_at_hal_doc(self, model_files):
        model, calib = model_files
        result = invoke(
            "--model", str(model),
            "--calibration", str(calib),
            "--target", "aie",
        )
        assert result.exit_code == 2
        assert "accelerator-hal-profiles.md" in result.output

    def test_default_output_path_derived(self, model_files):
        model, calib = model_files
        result = invoke(
            "--model", str(model),
            "--calibration", str(calib),
            "--target", "cmsis-nn",
            "--format", "int16",
        )
        assert "mobilenet.quantized.int16.tflite" in result.output

    def test_plan_echoes_inputs(self, model_files):
        model, calib = model_files
        result = invoke(
            "--model", str(model),
            "--calibration", str(calib),
            "--target", "cmsis-nn",
        )
        assert "Quantize plan" in result.output
        assert str(model) in result.output

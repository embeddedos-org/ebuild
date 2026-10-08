# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

from click.testing import CliRunner
import pytest
import subprocess

from ebuild.cli.commands import flash
from ebuild.core.config import load_config
import ebuild.firmware.flash


class DummyLogger:
    def header(self, msg):
        pass

    def step(self, msg):
        pass

    def info(self, msg):
        pass

    def success(self, msg):
        pass

    def error(self, msg):
        pass

    def warning(self, msg):
        pass

    def debug(self, msg):
        pass


def test_flash_config_parsing(tmp_path):
    """Test that load_config correctly parses the flash section."""
    config_file = tmp_path / "build.yaml"
    config_file.write_text(
        """
project:
  name: test
flash:
  runner_args: ["--adapter", "jlink"]
""",
        encoding="utf-8",
    )

    cfg = load_config(config_file)
    assert cfg.flash_config.get("runner_args") == ["--adapter", "jlink"]


@pytest.mark.parametrize(
    "config_args, env_args, cli_args, expected",
    [
        # runner args set only by config file
        (["--config-file-arg"], None, [], ["--config-file-arg"]),
        # runner args set only by env variable
        ([], "--env-arg", [], ["--env-arg"]),
        # runner args set only by CLI (with --)
        ([], None, ["--", "--cli-arg"], ["--cli-arg"]),
        # runner args set only by CLI (without --)
        ([], None, ["--cli-arg"], ["--cli-arg"]),
        # runner args set from env variable override config file
        (["--config-arg"], "--env-arg", [], ["--env-arg"]),
        # runner args set from CLI override env var
        ([], "--env-arg", ["--cli-arg"], ["--cli-arg"]),
        # runner args set from CLI override config file
        (["--config-arg"], None, ["--cli-arg"], ["--cli-arg"]),
        # runner args set from CLI override both env var and config file
        (["--config-arg"], "--env-arg", ["--cli-arg"], ["--cli-arg"]),
        # runner args set from CLI (multiple args)
        ([], None, ["--speed", "4000", "--reset"],
         ["--speed", "4000", "--reset"]),
        # explicitly clear args via CLI overrides both env var and config file
        (["--config-arg"], "--env-arg", ["--no-runner-args"], []),
        # no args at all
        ([], None, [], None),
    ],
)
def test_flash_args_combinations(
    tmp_path, monkeypatch, config_args, env_args, cli_args, expected
):
    """Test all combinations of config, env, and cli args precedence."""
    called_args = {}

    def mock_flash(*args, **kwargs):
        called_args.update(kwargs)

    monkeypatch.setattr(ebuild.firmware.flash, "flash", mock_flash)

    image = tmp_path / "dummy.bin"
    image.touch()

    # write the config file for testing
    config_file = tmp_path / "build.yaml"
    if config_args:
        args_str = ", ".join(f'"{a}"' for a in config_args)
        config_file.write_text(
            f"""
project:
  name: test
flash:
  runner_args: [{args_str}]
""",
            encoding="utf-8",
        )
    else:
        config_file.write_text("project:\n  name: test\n", encoding="utf-8")

    # set the env variable
    env = {}
    if env_args is not None:
        env["EBUILD_FLASH_RUNNER_ARGS"] = env_args

    # run flash command with env, config and cli args defined in the test case
    runner = CliRunner()
    invoke_args = [str(image), "--config", str(config_file)] + cli_args

    result = runner.invoke(flash, invoke_args, env=env, obj=DummyLogger())
    assert result.exit_code == 0, result.output

    if expected is None:
        assert not called_args.get("extra_args")
    else:
        assert called_args.get("extra_args") == expected


@pytest.mark.parametrize(
    "tool, extra_args, expected_cmd",
    [
        (
            "openocd",
            ["-c", "adapter speed 4000"],
            [
                "openocd",
                "-f", "interface/stlink.cfg",
                "-f", "target/stm32f4.cfg",
                "-c", "adapter speed 4000",
                "-c", "program {{{image_path}}} 0x8000000 verify reset exit",
            ],
        ),
        (
            "esptool",
            ["--port", "/dev/ttyUSB0", "--baud", "921600"],
            [
                "esptool.py",
                "--chip", "esp32",
                "--port", "/dev/ttyUSB0",
                "--baud", "921600",
                "write_flash", "0x8000000", "{image_path}",
            ],
        ),
        (
            "pyocd",
            ["--erase", "chip"],
            [
                "pyocd",
                "flash", "{image_path}",
                "--target", "stm32f4",
                "--base-address", "0x8000000",
                "--erase", "chip",
            ],
        ),
        (
            "nrfjprog",
            ["--reset", "--log"],
            [
                "nrfjprog",
                "--program", "{image_path}",
                "--sectorerase",
                "--verify",
                "--reset",
                "--log",
            ],
        ),
        (
            "stflash",
            ["--reset", "--serial", "1234"],
            [
                "st-flash",
                "--reset",
                "--serial", "1234",
                "write", "{image_path}", "0x8000000",
            ],
        ),
        # Test empty extra_args
        (
            "openocd",
            [],
            [
                "openocd",
                "-f", "interface/stlink.cfg",
                "-f", "target/stm32f4.cfg",
                "-c", "program {{{image_path}}} 0x8000000 verify reset exit",
            ],
        ),
    ],
)
def test_flash_extra_args_positioning_via_cli(
    tmp_path, monkeypatch, tool, extra_args, expected_cmd
):
    """
    Test that extra_args are correctly positioned
    when invoking the full CLI flash command.
    """
    image_path = tmp_path / "dummy.bin"
    image_path.touch()

    # we need a dummy build.yaml to prevent the load_config step from failing
    config_file = tmp_path / "build.yaml"
    config_file.write_text("project:\n  name: test\n", encoding="utf-8")

    captured_cmd = []

    def mock_subprocess_run(cmd, *args, **kwargs):
        captured_cmd.extend(cmd)
        return subprocess.CompletedProcess(
            args=cmd, returncode=0, stdout=b"", stderr=b""
        )

    monkeypatch.setattr(subprocess, "run", mock_subprocess_run)

    runner = CliRunner()
    invoke_args = [
        str(image_path),
        "--config", str(config_file),
        "--tool", tool,
        "--target", "stm32f4",
        "--address", "0x08000000",
    ]
    if extra_args:
        invoke_args.append("--")
        invoke_args.extend(extra_args)

    result = runner.invoke(flash, invoke_args, obj=DummyLogger())
    assert result.exit_code == 0, result.output

    expected_cmd = [
        arg.format(image_path=str(image_path)) for arg in expected_cmd
    ]

    assert captured_cmd == expected_cmd

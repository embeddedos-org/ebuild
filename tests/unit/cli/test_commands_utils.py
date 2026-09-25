# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

import pytest
from ebuild.cli.commands import _resolve_runner_args
from ebuild.core.config import load_config

class DummyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def info(self, msg): pass
    def error(self, msg): pass

def create_loader(config_path):
    return lambda: load_config(config_path)

@pytest.mark.parametrize(
    "config_val, env_val, cli_val, clear_args_val, expected",
    [
        # CLI priority short-circuits config
        (None, "--env-val", ("--cli-arg",), False, ["--cli-arg"]),
        # Env priority
        (None, "--env-val", (), False, ["--env-val"]),
        # Config priority
        (["--config-arg"], None, (), False, ["--config-arg"]),
        # None matches
        (None, None, (), False, []),
        # Valid config string parsing
        ("--adapter jlink", None, (), False, ["--adapter", "jlink"]),
        # Invalid config warns and falls back to empty
        (12345, None, (), False, []),
        # Explicit clear overrides config and env
        (["--config-arg"], "--env-val", (), True, []),
    ]
)
def test_resolve_runner_args_unit(tmp_path, monkeypatch, config_val, env_val, cli_val, clear_args_val, expected):
    """Directly unit test the _resolve_runner_args function combinations."""
    env_key = "TEST_ENV_KEY"
    if env_val is not None:
        monkeypatch.setenv(env_key, env_val)
    else:
        monkeypatch.delenv(env_key, raising=False)
        
    config_file = tmp_path / "build.yaml"
    if config_val is not None:
        if isinstance(config_val, list):
            args_str = ", ".join(f'"{a}"' for a in config_val)
            config_file.write_text(f'project:\n  name: test\nsystem:\n  test_args: [{args_str}]\n', encoding="utf-8")
        else:
            config_file.write_text(f'project:\n  name: test\nsystem:\n  test_args: {config_val}\n', encoding="utf-8")
            
    res = _resolve_runner_args(
        cli_args=cli_val, 
        env_key=env_key, 
        cfg_loader=create_loader(str(config_file)), 
        config_section="system_config", 
        config_key="test_args", 
        log=DummyLogger(),
        clear_args=clear_args_val,
    )
    assert res == expected

def test_resolve_runner_args_null_safety():
    """Verify null safety with empty or non-dict sections."""
    class FakeConfig:
        system_config = None # Explicitly None to test null safety
        
    res = _resolve_runner_args(
        cli_args=(), 
        env_key="TEST_ENV_KEY", 
        cfg_loader=lambda: FakeConfig(), 
        config_section="system_config", 
        config_key="test_args", 
        log=DummyLogger()
    )
    assert res == []


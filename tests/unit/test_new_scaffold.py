"""`ebuild new` must write every source its generated build.yaml declares."""
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from ebuild.cli.commands import cli

TEMPLATES = ["bare-metal", "ble-sensor", "rtos-app", "linux-app",
             "secure-boot", "safety-critical"]


@pytest.mark.parametrize("template", TEMPLATES)
def test_new_writes_every_declared_source(tmp_path: Path, template: str) -> None:
    result = CliRunner().invoke(
        cli, ["new", "proj", "--template", template, "--board", "stm32f4",
              "--output-dir", str(tmp_path)])
    assert result.exit_code == 0, result.output
    project = tmp_path / "proj"
    config = yaml.safe_load((project / "build.yaml").read_text(encoding="utf-8"))
    declared = [src for target in config["targets"] for src in target.get("sources", [])]
    assert declared, "template declares no sources"
    missing = [src for src in declared if not (project / src).is_file()]
    assert not missing, f"{template}: build.yaml declares missing sources {missing}"
    assert "{{" not in (project / "tests" / "test_main.c").read_text(encoding="utf-8")

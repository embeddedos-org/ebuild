import os
from pathlib import Path
import re
import subprocess
import sys

import pytest


INSTALLER = Path(__file__).resolve().parents[2] / "install.bat"

BATCH_COMMAND_PATTERN = re.compile(
    r'^\s*for /f "delims=" %%i in \(\''
    r'%PYTHON% -c "(?P<python>.+)"\'\) '
    r'do set SCRIPTS_DIR=%%i\s*$'
)


def _installer_python_commands():
    content = INSTALLER.read_text(encoding="utf-8")

    return [
        line
        for line in content.splitlines()
        if '-c "' in line
    ]


def test_embedded_python_commands_are_well_formed():
    """Installer Python commands must have valid batch and Python syntax."""
    lines = _installer_python_commands()

    assert lines, "No embedded Python commands found in install.bat"

    for line in lines:
        match = BATCH_COMMAND_PATTERN.fullmatch(line)

        assert match is not None, (
            f"Malformed FOR /F Python command in install.bat: {line}"
        )

        command = match.group("python")
        compile(command, "<install.bat>", "exec")


@pytest.mark.skipif(
    os.name != "nt",
    reason="Windows cmd.exe validation",
)
def test_embedded_python_commands_execute_in_cmd(tmp_path):
    """The complete FOR /F commands must execute successfully in cmd.exe."""
    lines = _installer_python_commands()

    assert len(lines) == 2

    batch_file = tmp_path / "validate_installer_commands.bat"

    script = "\r\n".join(
        [
            "@echo off",
            "setlocal",
            f'set "PYTHON={sys.executable}"',
            'set "SCRIPTS_DIR="',
            lines[0],
            "if not defined SCRIPTS_DIR exit /b 11",
            "echo FIRST=%SCRIPTS_DIR%",
            'set "SCRIPTS_DIR="',
            lines[1],
            "if not defined SCRIPTS_DIR exit /b 12",
            "echo SECOND=%SCRIPTS_DIR%",
            "endlocal",
        ]
    )

    batch_file.write_text(
        script,
        encoding="utf-8",
        newline="",
    )

    result = subprocess.run(
        ["cmd.exe", "/d", "/c", str(batch_file)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, (
        f"cmd.exe failed\nSTDOUT:\n{result.stdout}\n"
        f"STDERR:\n{result.stderr}"
    )

    assert "FIRST=" in result.stdout
    assert "SECOND=" in result.stdout

from pathlib import Path


INSTALLER = Path(__file__).resolve().parents[2] / "install.bat"


def test_embedded_python_commands_are_syntactically_valid():
    """Python snippets embedded in the Windows installer must be valid."""
    content = INSTALLER.read_text(encoding="utf-8")
    commands = []

    for line in content.splitlines():
        marker = '-c "'

        if marker not in line:
            continue

        start = line.index(marker) + len(marker)
        end = line.rfind('"')

        assert end > start, (
            f"Malformed embedded Python command in install.bat: {line}"
        )

        commands.append(line[start:end])

    assert commands, "No embedded Python commands found in install.bat"

    for command in commands:
        compile(command, "<install.bat>", "exec")

# Contributing to EoSuite

Thanks for your interest in contributing! This guide covers the workflow, coding standards, and **test requirements** for pull requests.

---

## 📋 Prerequisites

- **Python 3.10+** (with tkinter — included in standard CPython installs)
- Install dev dependencies:

```bash
pip install -r requirements-dev.txt
```

---

## 🔄 PR Workflow

1. **Fork & clone** the repository
2. **Create a branch** from `master`:
   ```bash
   git checkout -b feature/my-change
   ```
3. **Make your changes** — code, tests, docs
4. **Run lint + tests locally** (see below)
5. **Open a PR** against `master`

CI runs automatically on every PR: flake8 lint → pytest across 3 OS × 2 Python versions.

---

## 🧪 Testing Requirements

### Every PR Must Include Tests

- **New feature** → Add tests covering the feature's logic and edge cases
- **Bug fix** → Add a test that reproduces the bug and verifies the fix
- **Refactor** → Ensure existing tests still pass; update if behavior changes

### Running Tests

```bash
# Full suite (requires tkinter)
python -m pytest tests/ -v

# Headless only (no display needed)
python -m pytest tests/ -v -m "not gui"

# Single file
python -m pytest tests/test_eweb.py -v

# With coverage
python -m pytest tests/ --tb=short -q
```

### Test File Conventions

| Convention | Example |
|------------|---------|
| File naming | `tests/test_<module>.py` |
| Class naming | `class Test<Feature>:` |
| Function naming | `def test_<behavior>(self, ...):` |
| GUI tests | Mark with `@pytest.mark.gui` |
| Headless tests | No marker needed — runs everywhere |

### Writing a GUI Test

GUI tests use the `tk_root` session fixture from `conftest.py`. Create a mock app object with the theme colors dict:

```python
import tkinter as tk
import pytest


def _colors():
    return {
        "bg": "#1e1e1e", "fg": "#d4d4d4", "accent": "#0078d4",
        "sidebar_bg": "#252526", "toolbar_bg": "#2d2d2d",
        "tab_bg": "#2d2d2d", "tab_active": "#1e1e1e",
        "input_bg": "#3c3c3c", "input_fg": "#d4d4d4",
        "border": "#3c3c3c", "hover": "#094771",
        "button_bg": "#0e639c", "button_fg": "#ffffff",
        "status_bg": "#007acc", "status_fg": "#ffffff",
        "tree_bg": "#252526", "tree_fg": "#cccccc",
        "tree_select": "#094771", "menu_bg": "#2d2d2d",
        "menu_fg": "#cccccc", "terminal_bg": "#0c0c0c",
        "terminal_fg": "#cccccc",
    }


def _make_app():
    return type("App", (), {
        "theme": type("T", (), {"colors": _colors()})(),
        "set_status": lambda self, t: None,
    })()


@pytest.mark.gui
class TestMyFeature:
    def test_initial_state(self, tk_root):
        from gui.apps.my_module import MyWidget
        w = MyWidget(tk_root, _make_app())
        assert w.some_property == expected_value
```

### Writing a Headless Test (No GUI)

For pure-logic helpers (formatters, parsers, constants), write tests that don't need `tk_root`:

```python
class TestMyParser:
    def test_parses_input(self):
        from gui.apps.my_module import MyParser
        result = MyParser.parse("input")
        assert result == "expected"
```

### What to Test

| Area | What to Assert |
|------|----------------|
| **Initial state** | Default values, empty collections, flags |
| **State changes** | Toggle, connect/disconnect, activate/deactivate |
| **Input handling** | Valid input, empty input, edge cases |
| **Commands** | Each command produces expected output |
| **Formatting** | Size formatters, time formatters, string builders |
| **Boundary cases** | First/last page, max slots, empty lists |
| **Cleanup** | `on_close()` doesn't raise, resources released |

### Fixtures Available in `conftest.py`

| Fixture | Scope | Description |
|---------|-------|-------------|
| `tk_root` | session | Shared `tk.Tk()` root (withdrawn) for GUI tests |
| `theme` | function | Fresh `ThemeManager` instance |
| `tmp_sessions_file` | function | Temp sessions JSON path for `SessionManager` tests |
| `tmp_path` | function | Built-in pytest fixture for temp directories |

---

## 🧹 Code Style

- **Linter:** flake8 with `--max-line-length=120`
- **Formatting:** Follow existing patterns in `gui/apps/`
- **Imports:** Standard library → third-party → local, one per line
- **Docstrings:** Module-level docstring required for new files
- **No trailing whitespace** or unused imports in new code

Run lint locally before pushing:

```bash
python -m flake8 gui/ --max-line-length=120
```

---

## 📁 Project Structure

```
EoSuite/
├── gui/                    # Python GUI application
│   ├── apps/               # One file per tool (ecal.py, eweb.py, etc.)
│   ├── styles.py           # ThemeManager, DARK/LIGHT color dicts
│   ├── main_window.py      # Main application window
│   └── ...
├── src/                    # C source files
├── include/                # C headers
├── tests/                  # All test files
│   ├── conftest.py         # Shared fixtures (tk_root, theme, etc.)
│   ├── test_<module>.py    # Tests for each module
│   └── ...
├── .github/workflows/      # CI pipelines
│   ├── ci.yml              # Lint + test on PR
│   └── release.yml         # Build binaries on tag push
├── requirements-dev.txt    # Dev/test dependencies
└── pytest.ini              # Pytest configuration
```

---

## 🚀 CI Pipeline

Every PR triggers the **EoSuite CI** workflow:

1. **Lint** — flake8 on `gui/` source files
2. **Test** — pytest across 6 jobs:

| | Ubuntu | Windows | macOS |
|---|:---:|:---:|:---:|
| **Python 3.11** | ✅ | ✅ | ✅ |
| **Python 3.12** | ✅ | ✅ | ✅ |

Linux jobs use `xvfb-run` for headless GUI testing. All 6 jobs must pass before merging.

---

## 📝 PR Checklist

Before submitting your PR, verify:

- [ ] New/changed code has corresponding tests
- [ ] `python -m pytest tests/ -v` passes locally
- [ ] `python -m flake8 gui/ --max-line-length=120` passes locally
- [ ] Commit message is clear and descriptive
- [ ] No unrelated changes included

---

## 📜 License

By contributing, you agree that your contributions will be licensed under the MIT License.

# Customization & Plugin Development Guide

## Plugin System

ebuild supports plugins that hook into the build lifecycle, extend CLI commands, and customize package resolution. Plugins are discovered via Python [entry points](https://packaging.python.org/en/latest/specifications/entry-points/).

### Writing a Plugin

Create a Python package with a class that extends `PluginBase`:

```python
from ebuild.plugins.base import PluginBase, BuildContext, BuildResult

class MyPlugin(PluginBase):
    """Custom build plugin example."""

    name = "my-plugin"
    version = "0.1.0"

    def on_pre_build(self, context: BuildContext) -> None:
        """Called before build dispatch."""
        print(f"Building for target: {context.target}")

    def on_post_build(self, context: BuildContext, result: BuildResult) -> None:
        """Called after build completes."""
        if result.success:
            print(f"Build succeeded in {result.duration_s:.1f}s")

    def on_package_resolve(self, package_name: str, version: str) -> None:
        """Called when a package dependency is resolved."""
        print(f"Resolved: {package_name}@{version}")

    def on_hardware_analyze(self, profile) -> None:
        """Called after hardware analysis produces a profile."""
        print(f"Detected MCU: {profile.mcu}")

    def register_commands(self, cli) -> None:
        """Register custom CLI subcommands."""
        import click

        @cli.command()
        @click.argument("name")
        def greet(name):
            """Custom greeting command."""
            click.echo(f"Hello from my-plugin, {name}!")
```

### Registering a Plugin

Add an entry point to your `pyproject.toml`:

```toml
[project.entry-points."ebuild.plugins"]
my-plugin = "my_plugin:MyPlugin"
```

Then install your plugin package:

```bash
pip install -e ./my-plugin
```

ebuild discovers and loads all registered plugins at startup.

### Plugin Hooks Reference

| Hook | When Called | Parameters |
|------|-----------|------------|
| `on_pre_build` | Before build dispatch | `BuildContext` (target, config, build_dir) |
| `on_post_build` | After build completes | `BuildContext`, `BuildResult` (success, duration, artifacts) |
| `on_package_resolve` | When a dependency is resolved | package name, version string |
| `on_hardware_analyze` | After hardware analysis | `HardwareProfile` |
| `register_commands` | At CLI startup | Click `cli` group |

## Customizing Builds

### Build Profiles

ebuild supports composable build profiles that control which packages are included:

```yaml
# profiles/minimal.yaml
profile: minimal
description: "Bare minimum for boot + HAL"
packages:
  - core
  - hal
  - drivers
exclude:
  - networking
  - ai
  - graphics
  - filesystem
```

```yaml
# profiles/full.yaml
profile: full
description: "Everything including AI and networking"
packages:
  - core
  - hal
  - drivers
  - networking
  - filesystem
  - ai
  - graphics
  - crypto
  - ota
  - debug
```

Use a profile in your build:

```bash
ebuild build --target stm32h7 --profile minimal
```

### Writing Package Recipes

Package recipes are YAML files that describe external dependencies. Place them in the `recipes/` directory:

```yaml
# recipes/zlib.yaml
package: zlib
version: "1.3.1"
description: "General-purpose lossless data compression library"
license: Zlib
url: https://github.com/madler/zlib/releases/download/v1.3.1/zlib-1.3.1.tar.gz
checksum: sha256:9a93b2b7dfdac77ceba5a558a580e74667dd6fede4585b91eefb60f03b72df23
build: cmake
configure_args:
  - -DBUILD_SHARED_LIBS=OFF
  - -DSKIP_INSTALL_FILES=ON
dependencies: []
```

Recipe fields:

| Field | Required | Description |
|-------|----------|-------------|
| `package` | Yes | Package name |
| `version` | Yes | Version string |
| `url` | Yes | Source archive URL |
| `checksum` | No | `sha256:<hash>` for verification |
| `build` | No | Build system: `cmake`, `autoconf`, `make`, `meson`, `custom` (default: `cmake`) |
| `dependencies` | No | List of package names this depends on |
| `configure_args` | No | Extra args passed to configure/cmake |
| `build_args` | No | Extra args passed to build command |
| `patches` | No | List of patch file paths to apply |
| `description` | No | Human-readable description |
| `license` | No | SPDX license identifier |

### Layer Customization

To add a custom layer, create a directory under `layers/` with:

```
layers/my_layer/
├── CMakeLists.txt       # Build definition
├── include/             # Public headers
├── src/                 # Implementation
└── layer.yaml           # Layer metadata
```

Then enable it with:

```bash
ebuild build --target raspi4 --with my_layer
```

### Template Variables

When creating project templates in `templates/`, use `{{PLACEHOLDER}}` syntax:

| Variable | Description |
|----------|-------------|
| `{{PROJECT_NAME}}` | User-provided project name |
| `{{BOARD_NAME}}` | Selected board (e.g., `tms570`) |
| `{{ARCH}}` | Architecture (e.g., `arm`) |
| `{{CORE}}` | CPU core (e.g., `cortex-r5f`) |
| `{{TOOLCHAIN}}` | Toolchain name (e.g., `arm-none-eabi`) |
| `{{VENDOR}}` | Vendor name (e.g., `ti`) |
| `{{DATE}}` | Current date (YYYY-MM-DD) |
| `{{YEAR}}` | Current year |
# Customization & Plugin Development Guide

## Plugin System

ebuild supports plugins that hook into the build lifecycle, extend CLI commands, and customize package resolution. Plugins are discovered via Python [entry points](https://packaging.python.org/en/latest/specifications/entry-points/).

### Writing a Plugin

Create a Python package with a class that extends `PluginBase`:

```python
from ebuild.plugins.base import PluginBase, BuildContext, BuildResult

class MyPlugin(PluginBase):
    """Custom build plugin example."""

    name = "my-plugin"
    version = "0.1.0"

    def on_pre_build(self, context: BuildContext) -> None:
        """Called before build dispatch."""
        print(f"Building for target: {context.target}")

    def on_post_build(self, context: BuildContext, result: BuildResult) -> None:
        """Called after build completes."""
        if

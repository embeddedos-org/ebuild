# Getting Started

## Repository purpose

ebuild — Unified Embedded Build System

## First steps

1. Read the [README](https://github.com/embeddedos-org/ebuild/blob/master/README.md) for the project's supported setup and usage path.
2. Clone the repository and enter its directory:

```bash
git clone https://github.com/embeddedos-org/ebuild.git
cd ebuild
```

3. Check the root project inputs below before installing dependencies or selecting a build tool.
4. Review [Development](Development) before changing code, and [Security](Security) before reporting a vulnerability.

## Root project inputs

- `CMakeLists.txt`: CMake build definition.
- `Dockerfile`: Container build definition.
- `pyproject.toml`: Python project manifest.

## Scope note

The default branch inspected for this page was `master` at [`8b623d5786b5`](https://github.com/embeddedos-org/ebuild/commit/8b623d5786b5f841823f92a5506269f1e155a0f1). This page intentionally does not invent a universal build command when the repository's own documentation does not provide one.

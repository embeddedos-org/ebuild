# Changelog

## [Unreleased]

### Added
- **Remote Package Index & Synchronization (`ebuild/packages/index_sync.py`).**
  Downloads and validates central/mirror package repository indices into a local cache
  (`~/.ebuild/index/`), caching full recipe definitions. Enforces HTTPS transport,
  path-traversal sanitization (`^[a-zA-Z0-9_-]+$`), 10s socket timeouts, and 10MB response
  size limits. Index synchronization supports air-gapped operation via `--offline` and `EBUILD_OFFLINE=1`; package archive fetching is not yet offline-gated.
- **Package Discovery & Multi-Source Search (`ebuild search`, `ebuild/packages/repository.py`).**
  Search across local project recipes, system-shipped recipes, and cached remote indices.
  Supports `--all`, `--json`, `--build-system`, and `--license` filters.
- **Index Synchronization Command (`ebuild update-index`).**
  CLI command to refresh local package and recipe index caches from remote repositories.
- **Source-Ranked Recipe Precedence (`ebuild/packages/registry.py`).**
  Enforces strict 3-tier precedence hierarchy during package resolution: project-local recipes (`./recipes/`) > system-shipped recipes (`recipes/`) > cached remote index recipes (`~/.ebuild/index/recipes/`), guaranteeing reproducible builds (§9.2) and ensuring project-level pins override remote definitions.
- **Stale Cached Recipe Pruning (`ebuild/packages/index_sync.py`, `ebuild update-index`).**
  `ebuild update-index` automatically prunes stale cached `.yaml` and `.yml` recipes from `~/.ebuild/index/recipes/` that are absent from the newly synchronized remote package index. Surfaced the count of pruned recipes in CLI output and returned `SyncResult`.
- **Expanded Shipped Recipes Catalog (`recipes/`).**
  Added 5 verified recipes with HTTPS release pins and SHA-256 integrity digests:
  `cjson` (v1.7.18), `nanopb` (v0.4.9.1), `lvgl` (v9.2.2), `tinyusb` (v0.18.0), and `unity` (v2.6.1).

### Fixed

- **A path containing a space produced a silently wrong `build.ninja`.** Paths
  were written into build statements unescaped, but Ninja ends the output list
  at the first unescaped `:` and splits on unescaped spaces. A build directory
  under `C:\Users\Jane Doe\` parsed into four targets instead of one, so
  `ebuild build` failed with `expected build command name` or built the wrong
  thing. `$`, spaces and `:` are now escaped in generated build statements
  (`ebuild/build/ninja_backend.py`).
- **`NinjaBackend` could not generate anything.** `_object_path()` is called by
  both `_write_ninja()` and `_write_compile_commands()`, but the method itself
  was dropped in a merge, so every `generate()` raised
  `AttributeError: 'NinjaBackend' object has no attribute '_object_path'`.
  The method and its regression tests are restored: objects are named
  `obj/<target>/<source>.o`, so a source listed by two targets compiles once
  per target instead of both targets claiming one output — which ninja rejects
  with `multiple rules generate ...` (`ebuild/build/ninja_backend.py`).
- **`ebuild.build.dispatch` was unimportable.** Two branches independently added
  an unhandled-backend `else` clause to `BackendDispatcher.configure()`; the
  merge kept both, leaving a second `else` after the first and a `SyntaxError`
  that broke every command importing the module. The duplicate is removed and
  the two clauses are consolidated into one
  (`ebuild/build/dispatch.py`).
- **`configure(backend="ninja")` no longer silently succeeds.** `ebuild build`
  routes `backend: ninja` with no `targets` into the dispatcher, which has no
  ninja configure step; the no-op let the CLI report success having built
  nothing. It now raises with a message naming the missing `targets`
  (`ebuild/build/dispatch.py`).
- **Unhandled-backend errors no longer contradict themselves.** The message
  listed `ALL_BACKENDS` as supported, which includes `ninja` — the very backend
  being rejected. Each step now reports only the backends it handles
  (`ebuild/build/dispatch.py`).
- **Ninja backend: header changes now trigger a rebuild.** The generated `cc`
  rule declared no depfile, so Ninja only knew about the sources listed in
  `build.yaml`. Editing a header left stale object files in place and the build
  reported success. The rule now compiles with `-MMD -MF $out.d` and declares
  `depfile`/`deps`, so Ninja tracks the real include graph
  (`ebuild/build/ninja_backend.py`).
- **Package registry: versions that are not purely numeric no longer raise.**
  Version ordering parsed every dot-separated component with `int()`, so a
  recipe declaring `v2.9.3` -- the upstream tag form `recipes/littlefs.yaml`
  already downloads -- made `ebuild list-packages` fail with `ValueError`.
  Prereleases (`3.6.0-rc1`), distribution revisions (`1.2.13-1`) and build
  metadata (`1.0.0+build2`) failed the same way. It also replaced the
  resolver's actionable "package not found" error, which enumerates the
  registry, with a traceback. Dot-separated integers keep their numeric
  ordering; anything else is ranked below every numeric version and ordered
  lexicographically rather than guessed at (`ebuild/packages/registry.py`).
- **Declared targets are no longer overridden by backend auto-detection.**
  Backend detection inspects only the filesystem, so a `Makefile` kept for
  `make flash`, or a `CMakeLists.txt` belonging to one subcomponent, won over
  a `build.yaml` that declared its own `targets:`. The external tool ran, none
  of the declared targets were built, no build directory was produced, and
  `ebuild build` still reported "Build completed successfully" with exit code
  0. When the backend was auto-detected and targets are declared, the ninja
  backend is now used and the choice is logged. An explicit `backend:` in
  `build.yaml` or `--backend` still takes precedence (`ebuild/cli/commands.py`).
- **A relative `--build-dir` is now anchored to the project.** ebuild created
  and reported the build directory relative to the process working directory,
  while the ninja it launched read the same relative path from
  `cfg.source_dir`. The two agree only when the working directory is the
  project directory, so `ebuild build --config sub/build.yaml` failed with
  "ninja: error: loading '_build/build.ninja': No such file or directory" one
  line after reporting that it generated that file, and `ebuild configure`
  reported success having written it where a later build would not look. A
  relative `--build-dir` now resolves against the directory containing
  `build.yaml`, as an absolute path, so both sides agree regardless of the
  working directory (`ebuild/cli/commands.py`).

### Added
- `ebuild.build.dispatch.UnknownBackendError`, raised for a backend a dispatch
  step does not handle. It derives from both `ValueError` and `RuntimeError`
  because the clauses it replaces raised one each and callers depend on both —
  notably the CLI's `except RuntimeError`, which turns this into a clean
  `exit 1` rather than a traceback. New code should catch
  `UnknownBackendError`.

## [3.0.1] - 2026-05-16

### Production Release — Unified EmbeddedOS-org v3.0.1

This is the synchronized production release across all 18 EmbeddedOS-org repos.

- Refreshed governance: LICENSE, NOTICE, CITATION.cff, SECURITY.md
- CI/CD pipelines hardened: release.yml, book-build.yml, video-build.yml, deploy-pages.yml
- Release artifacts produced for: Linux x64/arm64, macOS x64/arm64, Windows x64, Docker, plus per-repo embedded/mobile/extension targets
- mdBook documentation built and deployed to GitHub Pages
- Promo video rendered and attached as a release asset

## [3.0.0] - 2026-05-13

### Production Release — Unified EmbeddedOS-org v3.0.0

This is the synchronized production release across all 18 EmbeddedOS-org repos.

- Refreshed governance: LICENSE, NOTICE, CITATION.cff, SECURITY.md
- CI/CD pipelines hardened: release.yml, book-build.yml, video-build.yml, deploy-pages.yml
- Release artifacts produced for: Linux x64/arm64, macOS x64/arm64, Windows x64, Docker, plus per-repo embedded/mobile/extension targets
- mdBook documentation built and deployed to GitHub Pages
- Promo video rendered and attached as a release asset

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-03-31

### Added
- Initial release of ebuild
- Unified monorepo build system for EoS ecosystem
- 18 CLI commands (build, clean, flash, test, analyze, sdk, release, etc.)
- Yocto-style SDK generation for 14 targets
- Deliverable packager (ZIP per target + manifest.json)
- Hardware analyzer (KiCad/YAML schematic parsing)
- Gated release pipeline (all repos must pass)
- Optional layer integration (eai, eni, eipc)
- Cross-compilation for aarch64, arm, riscv64
- Complete CI/CD pipeline with nightly, weekly, EoSim sanity, and simulation test runs
- Full cross-platform support (Linux, Windows, macOS)
- ISO/IEC standards compliance documentation
- MIT license

[0.1.0]: https://github.com/embeddedos-org/ebuild/releases/tag/v0.1.0
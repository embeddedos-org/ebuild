# Changelog

### Production Release — Unified EmbeddedOS-org v3.0.0

This is the synchronized production release across all 18 EmbeddedOS-org repositories.

- Refreshed governance: `LICENSE`, `NOTICE`, `CITATION.cff`, `SECURITY.md`
- CI/CD pipelines hardened: `release.yml`, `book-build.yml`, `video-build.yml`, `deploy-pages.yml`
- Release artifacts produced for Linux x64/arm64, macOS x64/arm64, Windows x64, Docker, plus per-repo embedded/mobile/extension targets
- mdBook documentation built and deployed to GitHub Pages
- Promo video rendered and attached as a release asset

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed

- **Dependency repositories now respect their remote default branch when no branch is configured.** ebuild no longer assumes `master` for unconfigured dependency repositories. When no branch is specified, Git uses the dependency repository's own default branch, allowing custom and third-party repositories whose default branch is `main` or another branch to be cloned correctly.

- Fixed handling of relative `--build-dir` paths.

### Added

- Improved support for dependency repository configuration and Git-based dependency management.

## [0.1.0] - 2026-03-31

### Added

- Initial release of ebuild
- Unified monorepo build system for EoS ecosystem
- 18 CLI commands (build, clean, flash, test, analyze, sdk, release, etc.)
- Yocto-style SDK generation for 14 targets
- Deliverable packager (ZIP per target + `manifest.json`)
- Hardware analyzer (KiCad/YAML schematic parsing)
- Gated release pipeline (all repos must pass)
- Optional layer integration (`eai`, `eni`, `eipc`)
- Cross-compilation for `aarch64`, `arm`, `riscv64`
- Complete CI/CD pipeline with nightly, weekly, EoSim sanity, and simulation test runs
- Full cross-platform support (Linux, Windows, macOS)
- ISO/IEC standards compliance documentation
- MIT license

[Unreleased]: https://github.com/embeddedos-org/ebuild/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/embeddedos-org/ebuild/releases/tag/v0.1.0

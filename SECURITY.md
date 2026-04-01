# Security Policy

## Supported Versions

| Version | Supported |
|---------|-----------|
| 0.1.x   | Yes       |

## Reporting a Vulnerability

Report security issues to: security@embeddedos.org

- Do NOT open public GitHub issues for vulnerabilities
- Include: description, reproduction steps, impact assessment
- Response within 48 hours, fix within 14 days for critical issues
- CVE assignment for confirmed vulnerabilities

## Supply Chain Security (ISO/IEC 20243)

- All releases include SBOM (sbom.json) in CycloneDX format
- Source provenance verified via SPDX license headers on all files
- Build reproducibility via ebuild SDK generator
- Dependency pinning via lockfiles

## Secure Development (ISO/IEC/IEEE 15288:2023)

- Static analysis on all C code (gcc -Wall -Wextra -Werror)
- Memory safety checks (no malloc in kernel, stack bounds)
- Crypto: SHA-256 (RFC 6234), AES-128/256, HMAC-SHA256
- Secure boot chain via eBoot (crypto verification)
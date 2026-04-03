# ISO/IEC 20243 — Open Trusted Technology Provider Standard

## Supply Chain Security

### Source Provenance
- All source files carry SPDX-License-Identifier headers
- Single monorepo with complete audit trail
- Git commit signing supported
- DCO (Developer Certificate of Origin) required for contributions

### Build Integrity
- ebuild CLI produces reproducible builds
- SDK generator creates deterministic toolchains per target
- Deliverable packager bundles source + SDK + binaries + manifest
- CycloneDX SBOM (sbom.json) lists all components

### Vulnerability Handling
- SECURITY.md defines reporting process
- 48-hour response SLA for reported vulnerabilities
- CVE assignment for confirmed issues
- Automated dependency scanning via CI

### Product Development Practices
- ISO C11 standard compliance
- Static analysis: gcc -Wall -Wextra
- No dynamic memory allocation in safety-critical paths
- Return value checking on all API calls
- NULL parameter validation on public interfaces

### Threat Analysis

| Threat | Mitigation |
|---|---|
| Firmware tampering | SHA-256 verification in OTA, eBoot secure boot |
| Supply chain injection | SPDX headers, SBOM, build reproducibility |
| Memory corruption | No malloc in kernel, stack bounds checking |
| Unauthorized access | HMAC-SHA256 (EIPC), AES encryption, RSA signatures |
| Replay attacks | EIPC nonce tracking, replay protection |
| Boot compromise | eBoot A/B slots, recovery partition, crypto verify |
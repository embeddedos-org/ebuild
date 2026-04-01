# eBootloader Security Model

## Phased Security Approach

eBootloader uses an incremental security model. The idea is to start
with a correct, simple system and layer complexity only when needed.

## Phase 1: Minimum Viable Protection

Available now in the initial codebase.

### CRC32 Integrity Checks
- Every firmware image has a CRC32 in its header hash field
- The boot manager verifies CRC32 before jumping to any image
- Boot control blocks carry CRC32 to detect corruption

### Version Comparison
- Image headers include a version field (major.minor.patch)
- The `eos_image_check_version()` API enables anti-rollback policies
- Firmware services expose version info to the application

### Redundant Metadata
- Boot control block is stored in two independent flash sectors
- If the primary copy is corrupt, the backup is used
- Both copies are written on every metadata update

### Anti-Tearing Writes
- Write sequence: compute CRC → erase primary → write primary → erase backup → write backup
- Power loss at any point leaves at least one valid copy

## Phase 2: Production-Grade Protection

Planned for future releases.

### SHA-256 Image Hash
- Replace CRC32 with a full SHA-256 hash in the header
- `sign_image.py --method sha256` already generates SHA-256 hashes
- Firmware verification reads the hash and recomputes over the payload

### Ed25519 / ECDSA Signature Verification
- The image header has a 64-byte signature field
- `sig_type` field indicates the signature algorithm
- Public key is embedded in the stage-1 boot code (cannot be modified)
- Signature verification happens in `eos_image_verify_signature()`

### Anti-Rollback Counters
- A monotonic counter stored in a dedicated flash region
- Each firmware release increments the counter
- Older firmware versions cannot be installed

## Phase 3: Advanced Security

### Payload Encryption
- Images can be encrypted (AES-256-CBC or AES-256-GCM)
- Decryption key stored in hardware secure storage (OTP / eFuse)
- `EOS_IMG_FLAG_ENCRYPTED` flag in the image header

### Recovery Authorization
- Recovery mode requires authentication (shared secret or challenge-response)
- Prevents unauthorized firmware replacement via physical access

### Secure Boot Chain
- Stage-0 verifies stage-1 before jumping
- Stage-1 verifies application before jumping
- Full chain of trust from ROM to application

## Design Rules

1. **Do not start with maximum complexity.** A correct CRC-based boot
   path is better than a broken signature implementation.

2. **Security features should be additive.** Phase 1 code should work
   unchanged when Phase 2 features are added.

3. **Never store secrets in flash alongside firmware.** Use hardware
   secure storage (OTP, eFuse, secure enclave) for keys.

4. **Recovery mode is a security boundary.** Physical access to UART
   should require authentication in production builds.

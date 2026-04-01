# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

#!/usr/bin/env python3
"""
sign_image.py — eBootloader Image Signing Tool

Signs an existing .eimg file with a digital signature.
Phase 1 supports CRC32 only. Phase 2+ will add Ed25519/ECDSA.

Usage:
    python sign_image.py --image firmware.eimg --method crc32
    python sign_image.py --image firmware.eimg --method ed25519 --key private.pem
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path

EOS_IMG_MAGIC = 0x454F5349
EOS_HASH_SIZE = 32
EOS_SIG_MAX_SIZE = 64

SIG_NONE = 0
SIG_CRC32 = 1
SIG_SHA256 = 2
SIG_ED25519 = 3


def verify_header(data: bytes) -> dict:
    """Parse and verify an image header, return header fields."""
    if len(data) < 24:
        raise ValueError("File too small for image header")

    magic = struct.unpack_from('<I', data, 0)[0]
    if magic != EOS_IMG_MAGIC:
        raise ValueError(f"Bad magic: 0x{magic:08X} (expected 0x{EOS_IMG_MAGIC:08X})")

    hdr_version, hdr_size = struct.unpack_from('<HH', data, 4)
    image_size, load_addr, entry_addr, image_version, flags = \
        struct.unpack_from('<IIIII', data, 8)

    return {
        'hdr_version': hdr_version,
        'hdr_size': hdr_size,
        'image_size': image_size,
        'load_addr': load_addr,
        'entry_addr': entry_addr,
        'image_version': image_version,
        'flags': flags,
    }


def sign_crc32(image_path: Path):
    """Update the CRC32 in the image header hash field."""
    data = bytearray(image_path.read_bytes())
    hdr = verify_header(data)
    hdr_size = hdr['hdr_size']
    image_size = hdr['image_size']

    payload = data[hdr_size:hdr_size + image_size]
    crc = zlib.crc32(bytes(payload)) & 0xFFFFFFFF

    # Write CRC32 to hash field (offset 28 in the header)
    hash_offset = 28  # 4+2+2+4+4+4+4+4 = 28
    struct.pack_into('<I', data, hash_offset, crc)

    # Set sig_type to CRC32
    sig_type_offset = hash_offset + EOS_HASH_SIZE  # 28 + 32 = 60
    data[sig_type_offset] = SIG_CRC32
    data[sig_type_offset + 1] = 0  # sig_len = 0 for CRC32

    image_path.write_bytes(bytes(data))
    print(f"CRC32 signature applied: 0x{crc:08X}")


def sign_sha256(image_path: Path):
    """Compute SHA-256 hash and store in the header."""
    import hashlib

    data = bytearray(image_path.read_bytes())
    hdr = verify_header(data)
    hdr_size = hdr['hdr_size']
    image_size = hdr['image_size']

    payload = data[hdr_size:hdr_size + image_size]
    sha = hashlib.sha256(bytes(payload)).digest()

    hash_offset = 28
    data[hash_offset:hash_offset + EOS_HASH_SIZE] = sha

    sig_type_offset = hash_offset + EOS_HASH_SIZE
    data[sig_type_offset] = SIG_SHA256
    data[sig_type_offset + 1] = 0

    image_path.write_bytes(bytes(data))
    print(f"SHA-256 hash applied: {sha.hex()}")


def main():
    parser = argparse.ArgumentParser(description='eBootloader Image Signing Tool')
    parser.add_argument('--image', '-i', required=True, help='Image file (.eimg)')
    parser.add_argument('--method', '-m', required=True,
                        choices=['crc32', 'sha256', 'ed25519'],
                        help='Signing method')
    parser.add_argument('--key', '-k', help='Private key file (for ed25519)')
    parser.add_argument('--verify', action='store_true', help='Verify instead of sign')

    args = parser.parse_args()
    image_path = Path(args.image)

    if not image_path.exists():
        print(f"Error: image not found: {args.image}", file=sys.stderr)
        sys.exit(1)

    if args.method == 'crc32':
        sign_crc32(image_path)
    elif args.method == 'sha256':
        sign_sha256(image_path)
    elif args.method == 'ed25519':
        print("Ed25519 signing not yet implemented (Phase 2)", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

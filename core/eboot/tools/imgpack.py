# SPDX-License-Identifier: MIT
# Copyright (c) 2026 EoS Project

#!/usr/bin/env python3
"""
imgpack.py — eBootloader Image Packer

Packs a raw firmware binary into an eBootloader image with
a proper header (magic, version, CRC32, addresses).

Usage:
    python imgpack.py --input firmware.bin --output firmware.eimg \
        --version 1.0.0 --load-addr 0x08010000 --entry-addr 0x08010000
"""

import argparse
import struct
import sys
import zlib
from pathlib import Path


EOS_IMG_MAGIC = 0x454F5349
EOS_IMAGE_HDR_VERSION = 1
EOS_HASH_SIZE = 32
EOS_SIG_MAX_SIZE = 64

# Signature types
SIG_NONE = 0
SIG_CRC32 = 1


def parse_version(version_str: str) -> int:
    """Parse 'major.minor.patch' into uint32 encoding."""
    parts = version_str.split('.')
    if len(parts) != 3:
        raise ValueError(f"Version must be major.minor.patch, got '{version_str}'")
    major, minor, patch = int(parts[0]), int(parts[1]), int(parts[2])
    return (major << 24) | (minor << 16) | (patch & 0xFFFF)


def compute_crc32(data: bytes) -> int:
    """Compute CRC32 matching the firmware implementation."""
    return zlib.crc32(data) & 0xFFFFFFFF


def build_header(
    image_size: int,
    load_addr: int,
    entry_addr: int,
    image_version: int,
    image_crc: int,
    flags: int = 0,
) -> bytes:
    """Build the eos_image_header_t binary structure."""

    # Hash field: store CRC32 in first 4 bytes, rest zeroed
    hash_field = struct.pack('<I', image_crc) + b'\x00' * (EOS_HASH_SIZE - 4)

    # Header size = total packed size
    hdr_size = 4 + 2 + 2 + 4 + 4 + 4 + 4 + 4 + EOS_HASH_SIZE + 1 + 1 + 30 + EOS_SIG_MAX_SIZE

    header = struct.pack('<I', EOS_IMG_MAGIC)
    header += struct.pack('<H', EOS_IMAGE_HDR_VERSION)
    header += struct.pack('<H', hdr_size)
    header += struct.pack('<I', image_size)
    header += struct.pack('<I', load_addr)
    header += struct.pack('<I', entry_addr)
    header += struct.pack('<I', image_version)
    header += struct.pack('<I', flags)
    header += hash_field
    header += struct.pack('<B', SIG_CRC32)   # sig_type
    header += struct.pack('<B', 0)            # sig_len (no signature yet)
    header += b'\x00' * 30                    # reserved
    header += b'\x00' * EOS_SIG_MAX_SIZE      # signature placeholder

    assert len(header) == hdr_size, f"Header size mismatch: {len(header)} != {hdr_size}"
    return header


def main():
    parser = argparse.ArgumentParser(
        description='eBootloader Image Packer — creates .eimg images'
    )
    parser.add_argument('--input', '-i', required=True, help='Raw firmware binary')
    parser.add_argument('--output', '-o', required=True, help='Output .eimg file')
    parser.add_argument('--version', '-v', required=True, help='Image version (major.minor.patch)')
    parser.add_argument('--load-addr', required=True, help='Load address (hex)')
    parser.add_argument('--entry-addr', required=True, help='Entry address (hex)')
    parser.add_argument('--flags', default='0', help='Image flags (hex)')

    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    firmware_data = input_path.read_bytes()
    image_size = len(firmware_data)

    load_addr = int(args.load_addr, 16)
    entry_addr = int(args.entry_addr, 16)
    image_version = parse_version(args.version)
    flags = int(args.flags, 16)
    image_crc = compute_crc32(firmware_data)

    header = build_header(
        image_size=image_size,
        load_addr=load_addr,
        entry_addr=entry_addr,
        image_version=image_version,
        image_crc=image_crc,
        flags=flags,
    )

    output_path = Path(args.output)
    output_path.write_bytes(header + firmware_data)

    ver_major = (image_version >> 24) & 0xFF
    ver_minor = (image_version >> 16) & 0xFF
    ver_patch = image_version & 0xFFFF

    print(f"eBootloader Image Packed:")
    print(f"  Input:      {args.input} ({image_size} bytes)")
    print(f"  Output:     {args.output} ({len(header) + image_size} bytes)")
    print(f"  Version:    {ver_major}.{ver_minor}.{ver_patch}")
    print(f"  Load addr:  0x{load_addr:08X}")
    print(f"  Entry addr: 0x{entry_addr:08X}")
    print(f"  CRC32:      0x{image_crc:08X}")
    print(f"  Header:     {len(header)} bytes")


if __name__ == '__main__':
    main()

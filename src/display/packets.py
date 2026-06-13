from __future__ import annotations

import struct

STARTING_BYTE = b"\x01"
ENDING_BYTE = b"\x02"


def _get_checksum(data: bytes) -> bytes:
    """Sum all bytes, return as 2-byte little-endian."""
    return struct.pack("<H", sum(data))


def build_packet(payload: bytes) -> bytes:
    """Construct a packet with the given payload."""
    length = struct.pack("<h", len(payload) + 2)  # Payload length + checksum length
    checksum = _get_checksum(length + payload)

    return STARTING_BYTE + length + payload + checksum + ENDING_BYTE

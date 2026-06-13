from __future__ import annotations

import struct

STARTING_BYTE = b"\x01"
ENDING_BYTE = b"\x02"


def encode_uint16_little_endian(value: int) -> bytes:
    """Encode an integer as a 2-byte unsigned little-endian value.

    Binary protocols need a consistent way to represent numbers as bytes.
    This function converts a Python integer into exactly two bytes using
    little-endian byte ordering.

    Endianness describes the order in which multiple bytes of a number are
    stored:

    - Little-endian stores the least significant byte first.
      Example:
          300 = 0x012C -> b"\\x2C\\x01"

    - Big-endian stores the most significant byte first.
      Example:
          300 = 0x012C -> b"\\x01\\x2C"

    The protocol uses little-endian, so both the sender and receiver must
    use this ordering to interpret multi-byte values correctly.

    The value is encoded as an unsigned 16-bit integer ("uint16"). Unsigned
    integers can only represent zero and positive values, giving a range of
    0 to 65,535. This is appropriate for fields such as lengths and
    checksums, which cannot be negative.

    A signed 16-bit integer ("int16") would reserve space for negative
    numbers and have a range of -32,768 to 32,767, but is not needed for
    these protocol fields.

    Args:
        value: The non-negative integer to encode.

    Returns:
        A 2-byte little-endian representation of the integer.
    """
    return struct.pack("<H", value)


def build_packet(payload: bytes) -> bytes:
    """Construct a complete binary packet containing the given payload.

    The packet follows this structure:

        +-------------+----------+-------------+----------+-----------+
        | Start Byte  | Length   | Payload     | Checksum | End Byte  |
        +-------------+----------+-------------+----------+-----------+
        | 1 byte      | 2 bytes  | N bytes     | 2 bytes  | 1 byte    |
        +-------------+----------+-------------+----------+-----------+

    Protocol fields:

    Start Byte:
        A fixed marker (0x01) indicating the beginning of a packet.
        This allows the receiver to identify where a valid message starts
        when reading a stream of bytes.

    Length:
        A 2-byte little-endian unsigned integer containing the size of the
        payload plus the checksum size. The receiver uses this value to know
        how many bytes belong to the packet data section.

        It does not include the start byte, length field itself, or end byte.

    Payload:
        The actual data being transmitted. This contains the command,
        information, or content understood by the receiving device.
        The packet builder does not interpret the payload; it only wraps it
        with the required protocol fields.

    Checksum:
        A 2-byte little-endian unsigned integer used to verify data integrity.
        It is calculated by summing the length bytes and payload bytes.
        The receiver performs the same calculation and compares the result.
        If the values differ, the packet may have been corrupted during
        transmission.

    End Byte:
        A fixed marker (0x02) indicating the end of a packet. Together with
        the start byte, this allows the receiver to identify packet
        boundaries.

    Args:
        payload:
            The raw bytes containing the data to send.

    Returns:
        A bytes object containing the complete formatted packet.
    """
    length = encode_uint16_little_endian(len(payload) + 2)
    checksum = encode_uint16_little_endian(sum(length + payload))

    return STARTING_BYTE + length + payload + checksum + ENDING_BYTE

from __future__ import annotations

import math
import struct
from pathlib import Path
from typing import TYPE_CHECKING

from PIL.Image import Image, Resampling
from PIL.Image import open as pil_open
from PIL.ImageSequence import Iterator

from .packets import build_packet

HERE = Path(__file__).parent
DEFAULT_FRAME_DURATION_MS = 100


def make_gif_data(path: Path) -> list[bytes]:
    if not path.exists():
        raise FileNotFoundError(f"The file {path} does not exist.")

    gif = pil_open(path)
    if gif.format != "GIF" or getattr(gif, "is_animated", False) is False:
        raise ValueError("The provided file is not a GIF.")

    image_duration_pairs = _create_image_duration_pairs(gif)

    processed_frames = _collate_frames(image_duration_pairs)

    return _construct_packets(processed_frames)


def _create_image_duration_pairs(gif: Image) -> list[tuple[Image, int]]:
    return [
        (
            frame.copy().convert("RGB"),
            frame.info.get(
                "duration",
                DEFAULT_FRAME_DURATION_MS,  # Use GIF's own frame duration if available
            ),
        )
        for frame in Iterator(gif)
    ]


def _encode_image(image: Image) -> tuple[bytes, bytes, int]:
    image = image.convert("RGB").resize((16, 16), Resampling.NEAREST)

    unique_colours: list[tuple[int, int, int]] = []
    colour_to_index_map: dict[tuple[int, int, int], int] = {}
    pixel_to_colour_index: list[int] = []

    for colour in image.getdata():
        if TYPE_CHECKING:
            assert isinstance(colour, tuple) and len(colour) == 3

        if colour not in unique_colours:
            # Gets the next available index for this new colour
            colour_to_index_map[colour] = len(unique_colours)

            # Add the new colour to the list of unique colours
            unique_colours.append(colour)

        # Append the corresponding colour index to the pixel data list
        pixel_to_colour_index.append(colour_to_index_map[colour])

    # Convert the list of unique colours to bytes (R, G, B for each colour)
    colour_data = b"".join(bytes(colour) for colour in unique_colours)

    # Calculate the number of bits needed to represent the colour indices
    num_colours = len(unique_colours)
    bits_per_pixel = max(1, math.ceil(math.log2(num_colours)))

    # Pack the pixel indices into a compact byte representation
    pixel_data = _pack_bits(pixel_to_colour_index, bits_per_pixel)

    return colour_data, pixel_data, num_colours


def _pack_bits(indices: list[int], bits_per_pixel: int) -> bytes:
    buffer = 0
    bit_count = 0
    output = bytearray()

    for index in indices:
        buffer |= index << bit_count
        bit_count += bits_per_pixel

        while bit_count >= 8:
            output.append(buffer & 0xFF)
            buffer >>= 8
            bit_count -= 8

    if bit_count:
        output.append(buffer & 0xFF)

    return bytes(output)


def _collate_frames(raw_frames: list[tuple[Image, int]]) -> list[bytes]:
    frame_parts = []

    for img, duration_ms in raw_frames:
        colour_data, pixel_data, num_of_colours = _encode_image(img)

        truncated_num_of_colours = num_of_colours & 0xFF

        inner_bytes = (
            struct.pack("<h", duration_ms)  # TT
            + b"\x00"  # R: reset palette each frame
            + bytes([truncated_num_of_colours])  # N
            + colour_data
            + pixel_data
        )
        frame_length = len(inner_bytes) + 3  # LL: inner length and A + LL, to get to next start
        frame_parts.append(b"\xaa" + struct.pack("<h", frame_length) + inner_bytes)

    return frame_parts


def _construct_packets(processed_frames: list[bytes]) -> list[bytes]:
    all_frames = b"".join(processed_frames)
    total_size = len(all_frames)

    packets = []

    start_payload = bytes([0x8B, 0x00]) + struct.pack("<I", total_size)
    packets.append(build_packet(start_payload))

    for offset_id, i in enumerate(range(0, total_size, 256)):
        chunk = all_frames[i : i + 256]
        data_payload = (
            bytes([0x8B, 0x01])
            + struct.pack("<I", total_size)
            + struct.pack("<H", offset_id)
            + chunk
        )
        packets.append(build_packet(data_payload))

    return packets

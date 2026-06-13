from __future__ import annotations

from pathlib import Path
from socket import AF_BLUETOOTH, BTPROTO_RFCOMM, SOCK_STREAM, socket
from time import sleep
from typing import Self

from src.display.gifs import make_gif_data
from src.logging import logger

RFCOMM_CHANNEL = 2
INTER_PACKET_DELAY = 0.04


class Divoom:
    def __init__(self, mac: str, channel: int = RFCOMM_CHANNEL):
        self.mac = mac
        self.channel = channel
        self.sock = socket(AF_BLUETOOTH, SOCK_STREAM, BTPROTO_RFCOMM)
        logger.debug(f"Initialized Divoom client for {mac}")

    def connect(self) -> None:
        logger.info(f"Connecting to device {self.mac} on RFCOMM channel {self.channel}")
        try:
            self.sock.connect((self.mac, self.channel))
            logger.info(f"Successfully connected to {self.mac}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.mac}: {e}", exc_info=True)
            raise

    def disconnect(self) -> None:
        try:
            self.sock.close()
            logger.info(f"Disconnected from {self.mac}")
        except Exception as e:
            logger.error(f"Error disconnecting from {self.mac}: {e}", exc_info=True)

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(self, exc_type, exc_value, traceback) -> None:
        if exc_type is not None:
            logger.error(f"Context manager exited with exception: {exc_type.__name__}: {exc_value}")
        self.disconnect()

    def send(self, data: bytes) -> None:
        try:
            logger.debug(f"Sending {len(data)} bytes")
            self.sock.sendall(data)
        except Exception as e:
            logger.error(f"Failed to send data: {e}", exc_info=True)
            raise

    def send_packets(self, packets: list[bytes], delay: float = INTER_PACKET_DELAY) -> None:
        logger.info(f"Sending {len(packets)} packets with {delay}s inter-packet delay")
        for i, packet in enumerate(packets, 1):
            try:
                self.send(packet)
                if i < len(packets):
                    sleep(delay)
            except Exception as e:
                logger.error(f"Failed to send packet {i}/{len(packets)}: {e}", exc_info=True)
                raise

    def receive(self, buffer_size: int = 1024) -> bytes:
        try:
            data = self.sock.recv(buffer_size)
            logger.debug(f"Received {len(data)} bytes")
            return data
        except Exception as e:
            logger.error(f"Failed to receive data: {e}", exc_info=True)
            raise

    def send_gif(self, path: Path) -> None:
        logger.info(f"Sending GIF from {path}")
        try:
            packets = make_gif_data(path)
            self.send_packets(packets)
            logger.info(f"Successfully sent GIF from {path}")
        except Exception as e:
            logger.error(f"Failed to send GIF from {path}: {e}", exc_info=True)
            raise

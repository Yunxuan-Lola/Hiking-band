"""Version 1 BLE packet: type, sequence, milliseconds, and x/y/z in mg.

Exactly 15 bytes, so a notification fits the default ATT MTU of 23 bytes.
"""
import struct
from dataclasses import dataclass

PACKET = struct.Struct('<BHIhhhH')
VERSION_TYPE = 0x11


@dataclass(frozen=True)
class Sample:
    sequence: int
    timestamp_ms: int
    x_g: float
    y_g: float
    z_g: float
    dropped: int


def decode(payload):
    if len(payload) != PACKET.size:
        raise ValueError('invalid sample packet length')
    kind, seq, timestamp, x, y, z, dropped = PACKET.unpack(payload)
    if kind != VERSION_TYPE:
        raise ValueError('unsupported packet type or version')
    return Sample(seq, timestamp, x / 1000., y / 1000., z / 1000., dropped)

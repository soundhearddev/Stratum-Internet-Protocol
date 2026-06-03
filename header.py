import struct
import hashlib
import secrets
import time
from enum import IntEnum

# Hinweis: Die Imports 'load_public_key' und 'gen_conn_id' wurden hier entfernt,
# da die Generierung jetzt komplett in die Fragmentierung wandert.

PROTOCOL_VERSION = 1
MAGIC            = 0x4D455348  # "MESH"

class PacketType(IntEnum):
    DATA      = 0x01
    ACK       = 0x02
    CONTROL   = 0x03
    ERROR     = 0x04
    HANDSHAKE = 0x05
    MIGRATION = 0x06

class Priority(IntEnum):
    REALTIME = 0x00
    HIGH     = 0x01
    NORMAL   = 0x02
    BULK     = 0x03

FLAG_ENCRYPTED       = 0x01
FLAG_FORWARD_SECRECY = 0x02
FLAG_MIGRATION       = 0x04
FLAG_LAST_FRAGMENT   = 0x08

# ----------------------------
# Header Layout (60 Bytes)
#
# Offset  Size  Field
# 0       4     Magic
# 4       1     Version
# 5       1     PacketType
# 6       1     Priority
# 7       1     Flags
# 8       16    Source mesh-addr
# 24      16    Destination mesh-addr
# 40      8     Connection ID
# 48      4     Sequence Number
# 52      4     ACK Number
# 56      2     Payload Length
# 58      1     Path ID
# 59      1     Congestion Hint
# + 8     Timestamp (unix)  → total 64 Bytes
# ----------------------------
HEADER_FORMAT = "!IBBBB16s16sQIIHBBQ"
HEADER_SIZE   = struct.calcsize(HEADER_FORMAT)
AUTH_TAG_SIZE = 16

def build_packet(
    src:       str,
    dst: str,
    payload:   bytes,
    ptype:     PacketType = PacketType.DATA,
    priority:  Priority   = Priority.NORMAL,
    conn_id:   int        = 0,  # Wird jetzt direkt so übernommen, wie übergeben
    seq:       int        = 0,
    ack:       int        = 0,
    path_id:   int        = 0,
    cong_hint: int        = 0,
    flags:     int        = FLAG_ENCRYPTED,
) -> bytes:

    src_bytes = bytes.fromhex(src)[:16]
    dst_bytes = bytes.fromhex(dst)[:16]
    
    # Der Zeitstempel des individuellen Pakets
    ts = time.time_ns()

    # REFACTOR: Kein 'if conn_id == 0:' Kladderadatsch mehr. 
    # build_packet packt einfach stur die ID ein, die du ihr gibst.

    header = struct.pack(
        HEADER_FORMAT,
        MAGIC,
        PROTOCOL_VERSION,
        int(ptype),
        int(priority),
        flags,
        src_bytes,
        dst_bytes,
        conn_id,  # Verwendet brav die ID aus der Fragmentierungs-Session
        seq,
        ack,
        len(payload),
        path_id,
        cong_hint,
        ts,
    )

    auth_tag = hashlib.sha256(header + payload).digest()[:AUTH_TAG_SIZE]
    return header + payload + auth_tag

def parse_packet(data: bytes) -> dict | None:
    if len(data) < HEADER_SIZE + AUTH_TAG_SIZE:
        return None

    try:
        (
            magic, version, ptype, priority, flags,
            src, dst,
            conn_id, seq, ack,
            payload_len, path_id, cong_hint, timestamp
        ) = struct.unpack(HEADER_FORMAT, data[:HEADER_SIZE])
    except struct.error:
        return None

    if magic != MAGIC:
        return None

    payload  = data[HEADER_SIZE:HEADER_SIZE + payload_len]
    auth_tag = data[HEADER_SIZE + payload_len:HEADER_SIZE + payload_len + AUTH_TAG_SIZE]

    expected = hashlib.sha256(data[:HEADER_SIZE] + payload).digest()[:AUTH_TAG_SIZE]
    if not secrets.compare_digest(auth_tag, expected):
        return None

    return {
        "version":   version,
        "type":      PacketType(ptype),
        "priority":  Priority(priority),
        "flags":     flags,
        "src":       src.hex(),
        "dst":       dst.hex(),
        "conn_id":   conn_id,
        "seq":       seq,
        "ack":       ack,
        "path_id":   path_id,
        "cong_hint": cong_hint,
        "timestamp": timestamp,
        "payload":   payload,
        "auth_ok":   True,
    }

if __name__ == "__main__":
    src = "fbfe3f0f1530d41a60a81c6d84a6e4d9"
    dst = "a3f9b2c8d4e1f5a6b7c8d9e0f1a2b3c4"
    data = "Hallo Welt".encode()

    # Test mit einer manuell gesetzten Test-Session-ID
    test_session_id = 999888777666
    pkt = build_packet(src, dst, data, priority=Priority.HIGH, conn_id=test_session_id)
    print(f"Paket  : {len(pkt)} Bytes (Header {HEADER_SIZE} + Payload + Auth {AUTH_TAG_SIZE})")

    p = parse_packet(pkt)
    if p:
        print(f"ConnID : {p['conn_id']} (Sollte {test_session_id} sein)")
        print(f"Auth   : {p['auth_ok']}")
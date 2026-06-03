"""
Overlay-Prototyp: mesh-Adressen über echtes Internet (IPv6/UDP Tunnel)
Registry: mesh-name → { mesh_addr, real_ipv6, port }
"""
import socket
import json
import sys
from pathlib import Path

REGISTRY_FILE = "./local_registry.json"
DEFAULT_PORT  = 9999
MAGIC         = b"MESH"

# ----------------------------
# Registry
# ----------------------------
def load_registry() -> dict:
    if Path(REGISTRY_FILE).exists():
        return json.loads(Path(REGISTRY_FILE).read_text())
    return {}

def register_peer(name: str, mesh_addr: str, real_ipv6: str, port: int = DEFAULT_PORT):
    reg = load_registry()
    reg[name] = {"address": mesh_addr, "ipv6": real_ipv6, "port": port}
    Path(REGISTRY_FILE).write_text(json.dumps(reg, indent=2))
    print(f"[+] {name} → mesh:{mesh_addr[:16]}...  real:{real_ipv6}")

def resolve(name: str) -> dict | None:
    return load_registry().get(name)

def resolve_by_mesh(mesh_addr: str) -> dict | None:
    for name, entry in load_registry().items():
        if entry["address"] == mesh_addr:
            return entry
    return None

# ----------------------------
# Packet
# Format: MESH + src_mesh(16B) + dst_mesh(16B) + payload_len(2B) + payload
# ----------------------------


def parse_packet(data: bytes) -> dict | None:
    if len(data) < 36 or data[:4] != MAGIC:
        return None
    src     = data[4:20].hex()
    dst     = data[20:36].hex()
    length  = int.from_bytes(data[36:38], "big")
    payload = data[38:38 + length]
    return {"src": src, "dst": dst, "payload": payload}

# ----------------------------
# Senden: mesh-Name → echte IPv6 aus Registry → UDP
# ----------------------------
def send(src_mesh: str, dst_name: str, payload: bytes):
    peer = resolve(dst_name)
    if not peer:
        raise ValueError(f"Unbekannt: {dst_name}")

    packet = build_packet(src_mesh, peer["address"], payload)

    print(f"[>] {dst_name}")
    print(f"    mesh : {peer['address']}")
    print(f"    real : {peer['ipv6']}:{peer['port']}")
    print(f"    bytes: {len(packet)}")

    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as s:
        s.sendto(packet, (peer["ipv6"], peer["port"]))

# ----------------------------
# Listener: empfängt echte IPv6 Pakete, liest mesh-Header
# ----------------------------
def listen(port: int = DEFAULT_PORT):
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("::", port))
        print(f"[*] Listening auf [::]:{port}")
        while True:
            data, addr = s.recvfrom(65535)
            pkt = parse_packet(data)
            if not pkt:
                print(f"[!] Ungültiges Paket von {addr[0]}")
                continue

            peer = resolve_by_mesh(pkt["src"])
            name = next((n for n, e in load_registry().items()
                         if e["address"] == pkt["src"]), "unbekannt")

            print(f"[<] Von {addr[0]} (mesh: {name})")
            print(f"    payload: {pkt['payload'].decode(errors='replace')}")

# ----------------------------
# CLI
# ----------------------------
if __name__ == "__main__":
    reg = load_registry()

    if "--register" in sys.argv:
        # python overlay.py --register homeserver.mesh fbfe3f0f... 2a01:4f8::1
        i = sys.argv.index("--register")
        register_peer(sys.argv[i+1], sys.argv[i+2], sys.argv[i+3])

    elif "--listen" in sys.argv:
        listen()

    elif "--send" in sys.argv:
        # python overlay.py --send homeserver.mesh "Hallo"
        i        = sys.argv.index("--send")
        dst      = sys.argv[i+1]
        msg      = sys.argv[i+2].encode() if len(sys.argv) > i+2 else b"ping"
        own_mesh = list(reg.values())[0]["address"]
        send(own_mesh, dst, msg)

    else:
        print("Registry:")
        for name, e in reg.items():
            print(f"  {name:30s} mesh:{e['address'][:16]}...  real:{e.get('ipv6','?')}")
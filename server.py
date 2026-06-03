"""
server.py - empfängt Handshake, antwortet mit eigenem, parsed weiter
"""
import json
import socket
import threading
from bootstrap import build_handshake
from registry import load_registry, save_registry, SUFFIX

HOST           = "::"
HANDSHAKE_PORT = 9998
MESH_PORT      = 9999

def handle_handshake(conn, addr):
    with conn:
        data    = conn.recv(65535)
        peer_hs = json.loads(data.decode())

        # eigenes Handshake zurückschicken
        own_hs = build_handshake()
        conn.sendall(json.dumps(own_hs).encode())

        # in Registry speichern
        _register(peer_hs, addr[0])

def _register(hs: dict, real_ipv6: str):
    name = hs["name"]  
    reg  = load_registry()
    reg[name] = {
        "address": hs["mesh_addr"],
        "pubkey":  hs["pubkey"],
        "ipv6":    real_ipv6,
        "port":    hs["port"],
    }
    save_registry(reg)
    print(f"[+] {name} → {hs['mesh_addr']}")

def handle_mesh(data: bytes, addr: tuple):
    # Platzhalter — overlay.parse_packet() kommt hier rein
    print(f"[<] Mesh-Paket von {addr[0]}: {len(data)} Bytes")

def tcp_listener():
    with socket.socket(socket.AF_INET6, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, HANDSHAKE_PORT))
        s.listen()
        print(f"[*] Handshake auf [::]:{HANDSHAKE_PORT}")
        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_handshake, args=(conn, addr), daemon=True).start()

def udp_listener():
    with socket.socket(socket.AF_INET6, socket.SOCK_DGRAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((HOST, MESH_PORT))
        print(f"[*] Mesh auf [::]:{MESH_PORT}")
        while True:
            data, addr = s.recvfrom(65535)
            threading.Thread(target=handle_mesh, args=(data, addr), daemon=True).start()

def start():
    threading.Thread(target=tcp_listener, daemon=True).start()
    threading.Thread(target=udp_listener, daemon=True).start()
    print("[*] Server läuft — Ctrl+C zum Beenden")
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("\n[*] Server gestoppt")

if __name__ == "__main__":
    start()
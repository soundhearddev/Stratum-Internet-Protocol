import os
import json
import time
from header import build_packet, parse_packet, PacketType, Priority

# Imports für die Session-ID-Generierung
from netIP import load_public_key
from utils import gen_conn_id

CHUNK_SIZE = 1200  
TMP_JSON_PATH = "packet_dump.json"

def fragment_data(
    data: bytes,
    src: str,
    dst: str,
    conn_id: int = 0,
    priority: Priority = Priority.NORMAL
):
    packets = []
    total = (len(data) + CHUNK_SIZE - 1) // CHUNK_SIZE

    # Einmalige Generierung der Connection ID für die gesamte Session
    if conn_id == 0:
        pub_bytes, _ = load_public_key()
        session_ts = time.time_ns() 
        conn_id = gen_conn_id(pub_bytes, session_ts)

    for seq in range(total):
        chunk = data[seq * CHUNK_SIZE:(seq + 1) * CHUNK_SIZE]

        # Last Fragment Flag setzen
        flags = 0x00
        if seq == total - 1:
            flags = 0x08  # FLAG_LAST_FRAGMENT

        pkt = build_packet(
            src=src,
            dst=dst,
            payload=chunk,
            ptype=PacketType.DATA,
            priority=priority,
            conn_id=conn_id,
            seq=seq,
            ack=0,
            path_id=0,  # Hier könnte man später verschiedene Pfade übergeben also so halt ob es im sleben mesh, außerhalb oder so
            cong_hint=0,
            flags=flags,
        )
        packets.append(pkt)

    return packets


def save_packets_to_json(packets: list, filename: str):
    """Parst die Pakete für die QoL-Vorschau und speichert Metadaten als JSON."""
    json_ready_data = []
    
    for i, pkt in enumerate(packets):
        parsed = parse_packet(pkt)
        if parsed:
            parsed["payload_len"] = len(parsed["payload"])
            parsed["payload_preview_hex"] = parsed["payload"][:10].hex() + "..."
            parsed["type"] = parsed["type"].name  
            parsed["priority"] = parsed["priority"].name  
            
            del parsed["payload"]  
            
            json_ready_data.append({
                "packet_index": i,
                "raw_packet_size_bytes": len(pkt),
                "metadata": parsed
            })

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(json_ready_data, f, indent=4)


if __name__ == "__main__":
    src = "fbfe3f0f1530d41a60a81c6d84a6e4d9"
    dst = "a3f9b2c8d4e1f5a6b7c8d9e0f1a2b3c4"
    filename = "linux.svg"

    # Automatischer Dummy-File-Generator, falls die Datei fehlt
    if not os.path.exists(filename):
        print(f"[*] '{filename}' nicht gefunden. Erstelle temporäre Dummy-Datei...")
        with open(filename, "wb") as f:
            f.write(os.urandom(3500)) 

    with open(filename, "rb") as f:
        data = f.read()
    
    print(f"[+] '{filename}' geladen ({len(data)} Bytes).")
    print("[-] Fragmentierung gestartet...")

    # Fragmentierung aufrufen
    packets = fragment_data(data, src, dst, priority=Priority.HIGH)

    # === ERWEITERTE TERMINAL TABELLE ===
    print("\n" + "=" * 110)
    print(f" MESH PROTOKOLL PROTOTYP: {len(packets)} Fragmente generiert")
    print("=" * 110)
    
    # Header-Zeile der Tabelle
    print(f"{'Idx':<4} | {'Typ':<6} | {'Prio':<8} | {'Seq':<4} | {'Größe':<9} | {'Path':<4} | {'Connection ID':<20} | {'Last?':<6} | {'SHA256 Auth':<10}")
    print("-" * 110)
    
    for i, p in enumerate(packets):
        parsed = parse_packet(p)
        
        if parsed:
            p_type   = parsed["type"].name
            p_prio   = parsed["priority"].name
            seq      = parsed["seq"]
            size     = f"{len(p)} B"
            path     = parsed["path_id"]
            c_id     = parsed["conn_id"]
            is_last  = "YES" if (parsed["flags"] & 0x08) else "NO"
            auth     = "VALID ✔" if parsed["auth_ok"] else "INVALID ❌"
        else:
            # Fallback falls beim Parsen etwas schiefgeht
            p_type = p_prio = size = auth = "ERR"
            seq = path = c_id = 0
            is_last = "NO"
        
        # Zeile formatiert ausgeben
        print(f"#{i:<3} | {p_type:<6} | {p_prio:<8} | #{seq:<2} | {size:<9} | ID {path:<2} | {c_id:<20} | {is_last:<6} | {auth:<10}")
        
    print("-" * 110)

    # In JSON wegsichern
    save_packets_to_json(packets, TMP_JSON_PATH)
    print(f"\n[v] Detaillierter Komplett-Dump erfolgreich in '{TMP_JSON_PATH}' gespeichert!")
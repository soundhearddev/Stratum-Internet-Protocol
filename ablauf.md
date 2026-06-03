SEND                                                            RECEIVE

[FILE / DATA (z.B. 100 MB)]                             +---------------------------+
            │                                           | Application Layer         |
            ▼                                           | - Datei / Message fertig  |
+---------------------------+                           +---------------------------+
| Fragmentation Layer       |                                     ▲
| - split in chunks         |                           +---------------------------+
| - seq / frag_index        |                           | Reassembly Layer          |
+---------------------------+                           | - Fragmente zusammenfügen |
            │                                           | - Reihenfolge sortieren   |
            ▼                                           +---------------------------+
+---------------------------+                                     ▲
| Packet Builder            |                           +---------------------------+
| - Header bauen            |                           | Packet Parser             |
| - ConnID setzen           |                           | - Header lesen            |
| - Payload anhängen        |                           | - ConnID / Seq / Flags    |
+---------------------------+                           | - Payload extrahieren     |
            │                                           +---------------------------+
            ▼                                                     ▲
+---------------------------+                           +---------------------------+
| Mesh / Translation Layer  |                           | Mesh / Translation Layer  |
| - mapping zu IPv6        |                           | - IPv6 → Mesh Paket       |
| - ggf. weitere headers    |                           | - Header entfernen        |
+---------------------------+                           +---------------------------+
            │                                                     ▲
            ▼                                                     ▲
+---------------------------+                           +---------------------------+
| IPv6 Stack                |                           | IPv6 Stack                |
| - MTU handling           |                           | - Routing / MTU Handling  |
| - routing                |                           +---------------------------+
+---------------------------+                                     ▲
            │                                                     ▲
            ▼                                                     ▲
        INTERNET                                      Physical / Link Layer
                                                     - WLAN / Ethernet
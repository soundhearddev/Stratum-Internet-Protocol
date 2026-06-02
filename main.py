import os
import sys
import addresses as net 


def main():
    if os.geteuid() != 0:
        print("✗ Bitte als root / mit sudo ausführen.")
        sys.exit(1)

    iface = net.get_default_iface()
    print(f"[*] Interface: {iface}")

    prefix = net.get_prefix_from_ra(iface)
    if not prefix:
        prefix = net.get_prefix_via_rdisc6(iface)
    if not prefix:
        print("✗ Kein IPv6-Präfix gefunden.")
        sys.exit(1)

    print(f"[*] Präfix: {prefix}/64")

    count = 5

    before = set(net.current_addresses(iface))

    print(f"[*] Erzeuge {count} neue Adressen...")

    net.build_address(count, prefix, before, iface)


    after = net.current_addresses(iface)
    
    print(f"[*] Gesamt jetzt: {len(after)}")


if __name__ == "__main__":
    main()
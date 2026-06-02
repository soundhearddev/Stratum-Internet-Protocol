
import subprocess
import secrets
import sys
import os
import re
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def get_default_iface() -> str:
    r = run(["ip", "-6", "route", "show", "default"])

    for line in r.stdout.splitlines():
        parts = line.split()
        if "dev" in parts:
            return parts[parts.index("dev") + 1]

    print("✗ Kein Default-Interface gefunden.")
    sys.exit(1)


def ensure_dummy_iface(name="ipwrap0") -> str:
    r = run(["ip", "link", "show", name])
    if r.returncode != 0:
        r = run(["ip", "link", "add", name, "type", "dummy"])
        if r.returncode != 0:
            print("✗ Konnte Interface nicht erstellen:", r.stderr.strip())
            sys.exit(1)

    run(["ip", "link", "set", name, "up"])
    return name


def get_prefix_from_ra(iface: str) -> str | None:
    r = run(["ip", "-o", "-6", "addr", "show", "dev", iface])
    for line in r.stdout.splitlines():
        if "scope global" not in line:
            continue
        m = re.search(r"inet6 ([0-9a-f:]+)/(\d+)", line)
        if not m:
            continue
        addr, plen = m.group(1), int(m.group(2))
        # Nur /64 oder kürzer (kein /128 = Privacy/Temp)
        if plen > 64:
            continue
        # Präfix-Gruppen extrahieren (erste 4 Gruppen = /64)
        groups = addr.split(":")
        # Expand "::" falls nötig
        if "::" in addr:
            full = expand_ipv6(addr)
            groups = full.split(":")
        prefix_groups = groups[:4]
        return ":".join(prefix_groups) + "::"
    return None


def expand_ipv6(addr: str) -> str:
    if "::" in addr:
        left, right = addr.split("::", 1)
        l = left.split(":") if left else []
        r = right.split(":") if right else []
        missing = 8 - len(l) - len(r)
        groups = l + ["0000"] * missing + r
    else:
        groups = addr.split(":")
    return ":".join(g.zfill(4) for g in groups)


def get_prefix_via_rdisc6(iface: str) -> str | None:
    r = run(["which", "rdisc6"])
    if r.returncode != 0:
        return None
    r = run(["rdisc6", "-1", iface])
    m = re.search(r"Prefix\s+:\s+([0-9a-f:]+)/(\d+)", r.stdout)
    if m:
        addr, plen = m.group(1), int(m.group(2))
        groups = expand_ipv6(addr).split(":")
        return ":".join(groups[:4]) + "::"
    return None


def random_suffix() -> str:
    return ":".join(f"{secrets.randbits(16):04x}" for _ in range(4))


def build_address(prefix: str) -> str:
    base = prefix.rstrip(":")
    return base + ":" + random_suffix() + "/64"


def current_addresses(iface: str) -> list[str]:
    r = run(["ip", "-o", "-6", "addr", "show", "dev", iface])
    return [line.split()[3] for line in r.stdout.splitlines() if line.strip()]


def add_address(iface: str, addr: str) -> bool:
    r = run(["ip", "-6", "addr", "add", addr, "dev", iface])
    return r.returncode == 0


def build_address(count=0, prefix="", before="", iface=""):
    for i in range(count):
        new_addr = build_address(prefix)

        while new_addr in before:
            new_addr = build_address(prefix)

        ok = add_address(iface, new_addr)

        if ok:
            print(f"[✓] {i+1}: {new_addr}")
            before.add(new_addr)
        else:
            print(f"[✗] Fehler bei {new_addr}")

    
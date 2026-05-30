#!/usr/bin/env python3
"""
marauder_parser.py  --  Deliverable 4.1
ESP32 Marauder scan-output / PCAP parser -> CSV + human-readable report.

================================================================================
WHAT THIS DOES
  * Parses two kinds of Marauder output:
      (1) The on-screen AP / Station scan list, exported as text/log. This is the
          noisy format shown on the Marauder display and dumped over serial.
      (2) A PCAP file captured by one of Marauder's "Sniff" modes (Beacon,
          Probe, etc.) -- ONLY if `scapy` is installed (optional dependency).
  * Emits one row per discovered network with: SSID, BSSID, channel, RSSI,
    encryption, WPS flag, first-seen / last-seen timestamps.
  * Writes a CSV and prints / writes a short human-readable summary report.

WHAT THIS DOES *NOT* DO
  * It does NOT transmit anything, touch any radio, or talk to the device.
    It is a pure offline file/stdin parser.
  * It does NOT decrypt traffic or crack keys.
  * It does NOT phone home -- no network calls of any kind.

--------------------------------------------------------------------------------
AUTHORIZED USE ONLY
  Use this only on data you captured from networks you own or are explicitly,
  in writing, authorized to assess. Passive capture and even network discovery
  can be regulated in your jurisdiction. You are responsible for compliance.
--------------------------------------------------------------------------------

DEPENDENCIES
  * Python 3.8+            (standard library only for text-log mode)
  * scapy   (OPTIONAL)     pip install scapy      # only for PCAP mode
    If scapy is missing, PCAP input is refused with a clear message and
    text-log parsing still works.

USAGE
  # Parse a serial/text dump of the on-screen AP scan:
  python3 marauder_parser.py --text scan_dump.txt --csv networks.csv --report report.txt

  # Read the text from stdin instead:
  cat scan_dump.txt | python3 marauder_parser.py --text - --csv networks.csv

  # Parse a PCAP from a Marauder sniff mode (needs scapy):
  python3 marauder_parser.py --pcap beacons.pcap --csv networks.csv --report report.txt

INPUT FORMAT (text mode), per Appendix B of the brief
  Entry line:   #<index> <RSSI> <channel> <SSID-or-BSSID>
                e.g.  "#17 -57 1 AIS_WAN_2.4G"
                - RSSI is negative dBm.
                - SSID may contain spaces; some rows show a raw BSSID instead.
  Status line:  "<name>: RXd WPS Configs"
                - NOT a new network. The WPS flag is attributed to the matching
                  SSID and the line is otherwise ignored.
"""

import argparse
import csv
import re
import sys
from collections import OrderedDict
from datetime import datetime, timezone

# -----------------------------------------------------------------------------
# Optional scapy import -- degrade gracefully if it is not installed.
# -----------------------------------------------------------------------------
try:
    from scapy.all import rdpcap, Dot11, Dot11Beacon, Dot11ProbeResp, Dot11Elt  # type: ignore
    _HAVE_SCAPY = True
except Exception:  # ImportError, or a broken install
    _HAVE_SCAPY = False


# A loose MAC/BSSID matcher: 6 hex pairs separated by ':'
_MAC_RE = re.compile(r"^(?:[0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$")

# Entry line:  #<idx> <rssi> <channel> <rest-is-ssid-or-bssid>
# RSSI is negative; channel is a small positive int. Keep the rest greedily.
_ENTRY_RE = re.compile(
    r"^#(?P<idx>\d+)\s+(?P<rssi>-?\d{1,3})\s+(?P<chan>\d{1,3})\s+(?P<rest>.+?)\s*$"
)

# Status line:  "<name>: RXd WPS Configs"   (case-insensitive on the suffix)
_WPS_RE = re.compile(r"^(?P<name>.+?):\s*RXd\s+WPS\s+Configs\s*$", re.IGNORECASE)


def _now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Network:
    """One discovered network. Keyed by SSID (text mode) or BSSID (pcap mode)."""

    __slots__ = (
        "ssid", "bssid", "channel", "rssi", "encryption",
        "wps", "first_seen", "last_seen", "hits",
    )

    def __init__(self, ssid="", bssid=""):
        self.ssid = ssid
        self.bssid = bssid
        self.channel = ""
        self.rssi = None          # keep the *strongest* (least negative) RSSI
        self.encryption = ""
        self.wps = False
        ts = _now_iso()
        self.first_seen = ts
        self.last_seen = ts
        self.hits = 0

    def observe(self, rssi=None, channel=None):
        self.hits += 1
        self.last_seen = _now_iso()
        if channel:
            self.channel = str(channel)
        if rssi is not None:
            try:
                r = int(rssi)
                if self.rssi is None or r > self.rssi:
                    self.rssi = r
            except (TypeError, ValueError):
                pass

    def as_row(self):
        return {
            "ssid": self.ssid,
            "bssid": self.bssid,
            "channel": self.channel,
            "rssi_dbm": "" if self.rssi is None else self.rssi,
            "encryption": self.encryption or "unknown",
            "wps": "yes" if self.wps else "no",
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "observations": self.hits,
        }


# -----------------------------------------------------------------------------
# Text / on-screen scan parsing
# -----------------------------------------------------------------------------
def parse_text(lines):
    """
    Parse the noisy on-screen AP scan. Returns an OrderedDict keyed by the
    network's display name (SSID or raw BSSID). Robust to junk lines.
    """
    nets = OrderedDict()
    skipped = 0

    for raw in lines:
        line = raw.rstrip("\r\n")
        if not line.strip():
            continue

        # 1) WPS status line?  Attribute the flag, do NOT create a network.
        m = _WPS_RE.match(line.strip())
        if m:
            name = m.group("name").strip()
            net = nets.get(name)
            if net is None:
                # Network announced its WPS before its entry line appeared;
                # create a placeholder so the flag is not lost.
                net = Network(ssid=name)
                nets[name] = net
            net.wps = True
            continue

        # 2) Entry line?
        m = _ENTRY_RE.match(line.strip())
        if m:
            rest = m.group("rest").strip()
            looks_like_bssid = bool(_MAC_RE.match(rest))
            ssid = "" if looks_like_bssid else rest
            bssid = rest if looks_like_bssid else ""
            # Key on the visible name so WPS placeholders merge correctly.
            key = rest
            net = nets.get(key)
            if net is None:
                net = Network(ssid=ssid, bssid=bssid)
                nets[key] = net
            else:
                # Fill in fields if the placeholder lacked them.
                if not net.ssid and ssid:
                    net.ssid = ssid
                if not net.bssid and bssid:
                    net.bssid = bssid
            net.observe(rssi=m.group("rssi"), channel=m.group("chan"))
            continue

        # 3) Anything else: a partial/garbled/status line we don't recognize.
        skipped += 1

    return nets, skipped


# -----------------------------------------------------------------------------
# PCAP parsing (optional, requires scapy)
# -----------------------------------------------------------------------------
def _crypto_from_beacon(pkt):
    """Best-effort encryption string from beacon/probe-resp capabilities + IEs."""
    enc = "OPEN"
    has_rsn = False        # WPA2/WPA3
    has_wpa = False        # WPA1 vendor IE
    has_wps = False
    try:
        cap = pkt.sprintf("{Dot11Beacon:%Dot11Beacon.cap%}{Dot11ProbeResp:%Dot11ProbeResp.cap%}")
        if "privacy" in cap:
            enc = "WEP"  # refined below if RSN/WPA present
    except Exception:
        pass

    elt = pkt.getlayer(Dot11Elt)
    while elt is not None and isinstance(elt, Dot11Elt):
        if elt.ID == 48:                      # RSN
            has_rsn = True
        elif elt.ID == 221:                   # vendor specific
            info = bytes(elt.info) if elt.info else b""
            if info[:4] == b"\x00\x50\xf2\x01":   # WPA1
                has_wpa = True
            if info[:4] == b"\x00\x50\xf2\x04":   # WPS
                has_wps = True
        elt = elt.payload.getlayer(Dot11Elt)

    if has_rsn:
        enc = "WPA2/WPA3"
    elif has_wpa:
        enc = "WPA"
    return enc, has_wps


def parse_pcap(path):
    if not _HAVE_SCAPY:
        raise RuntimeError(
            "PCAP parsing requires scapy, which is not installed.\n"
            "Install it with `pip install scapy`, or use --text mode instead."
        )
    nets = OrderedDict()
    packets = rdpcap(path)
    for pkt in packets:
        if not pkt.haslayer(Dot11):
            continue
        if not (pkt.haslayer(Dot11Beacon) or pkt.haslayer(Dot11ProbeResp)):
            continue
        d11 = pkt.getlayer(Dot11)
        bssid = (d11.addr3 or "").lower()
        if not bssid:
            continue

        ssid = ""
        chan = ""
        elt = pkt.getlayer(Dot11Elt)
        while elt is not None and isinstance(elt, Dot11Elt):
            if elt.ID == 0:  # SSID
                try:
                    ssid = elt.info.decode(errors="replace")
                except Exception:
                    ssid = ""
            elif elt.ID == 3 and elt.info:  # DS Parameter set -> channel
                chan = str(elt.info[0])
            elt = elt.payload.getlayer(Dot11Elt)

        enc, wps = _crypto_from_beacon(pkt)

        # RSSI: RadioTap dBm if present.
        rssi = None
        if hasattr(pkt, "dBm_AntSignal"):
            rssi = pkt.dBm_AntSignal

        net = nets.get(bssid)
        if net is None:
            net = Network(ssid=ssid, bssid=bssid)
            nets[bssid] = net
        if ssid and not net.ssid:
            net.ssid = ssid
        net.encryption = enc
        net.wps = net.wps or wps
        net.observe(rssi=rssi, channel=chan)

    return nets, 0


# -----------------------------------------------------------------------------
# Output
# -----------------------------------------------------------------------------
_FIELDS = [
    "ssid", "bssid", "channel", "rssi_dbm",
    "encryption", "wps", "first_seen", "last_seen", "observations",
]


def write_csv(nets, path):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=_FIELDS)
        w.writeheader()
        for net in nets.values():
            w.writerow(net.as_row())


def build_report(nets, skipped):
    total = len(nets)
    wps_count = sum(1 for n in nets.values() if n.wps)
    open_count = sum(1 for n in nets.values() if (n.encryption or "").upper() == "OPEN")
    chans = {}
    for n in nets.values():
        if n.channel:
            chans[n.channel] = chans.get(n.channel, 0) + 1

    lines = []
    lines.append("=" * 60)
    lines.append("Marauder scan summary")
    lines.append("Generated (UTC): " + _now_iso())
    lines.append("=" * 60)
    lines.append(f"Networks discovered : {total}")
    lines.append(f"WPS-flagged         : {wps_count}")
    lines.append(f"Open / unencrypted  : {open_count}")
    if chans:
        chan_str = ", ".join(f"ch{c}={n}" for c, n in sorted(chans.items(), key=lambda x: int(x[0])))
        lines.append(f"Channel occupancy   : {chan_str}")
    if skipped:
        lines.append(f"Unparsed lines      : {skipped} (malformed/partial, skipped safely)")
    lines.append("-" * 60)
    lines.append(f"{'RSSI':>5}  {'CH':>3}  {'WPS':>3}  {'ENC':<10}  NAME/BSSID")
    lines.append("-" * 60)
    # Strongest signal first.
    def _key(n):
        return (-(n.rssi if n.rssi is not None else -999),)
    for n in sorted(nets.values(), key=_key):
        name = n.ssid or n.bssid or "(hidden)"
        rssi = "" if n.rssi is None else n.rssi
        lines.append(
            f"{str(rssi):>5}  {n.channel:>3}  {'yes' if n.wps else ' no':>3}  "
            f"{(n.encryption or 'unknown'):<10}  {name}"
        )
    lines.append("=" * 60)
    return "\n".join(lines)


# -----------------------------------------------------------------------------
def main(argv=None):
    ap = argparse.ArgumentParser(description="Parse Marauder scan output -> CSV + report.")
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--text", metavar="FILE", help="text/log scan dump ('-' for stdin)")
    src.add_argument("--pcap", metavar="FILE", help="PCAP from a Marauder sniff mode (needs scapy)")
    ap.add_argument("--csv", metavar="FILE", default="networks.csv", help="output CSV path")
    ap.add_argument("--report", metavar="FILE", help="write report here (else print to stdout)")
    args = ap.parse_args(argv)

    if args.text:
        if args.text == "-":
            lines = sys.stdin.readlines()
        else:
            with open(args.text, "r", encoding="utf-8", errors="replace") as fh:
                lines = fh.readlines()
        nets, skipped = parse_text(lines)
    else:
        nets, skipped = parse_pcap(args.pcap)

    write_csv(nets, args.csv)
    report = build_report(nets, skipped)
    if args.report:
        with open(args.report, "w", encoding="utf-8") as fh:
            fh.write(report + "\n")
        print(f"[+] Wrote {len(nets)} networks -> {args.csv}")
        print(f"[+] Wrote report          -> {args.report}")
    else:
        print(report)
        print(f"\n[+] CSV written to {args.csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

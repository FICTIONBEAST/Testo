#!/usr/bin/env python3
"""
serial_bridge.py  --  Deliverable 4.2
Flipper Zero  <-> ESP32 (Marauder) serial bridge / automation.

================================================================================
WHAT THIS DOES
  * Opens a serial session to an ESP32 running Marauder.
  * Sends a defined command set and logs every response with timestamps.
  * Runs scripted sequences -- e.g. start a scan, wait N seconds, stop, dump
    results -- so you can collect data hands-free.

WHAT THIS DOES *NOT* DO
  * It does NOT itself transmit RF or perform attacks; it only relays text
    commands you choose to the Marauder console. The radio behaviour is
    entirely Marauder's. Choose commands responsibly.
  * It does NOT bypass Flipper firmware. When a Flipper is in the path it is
    acting purely as a USB-serial pass-through / power source (see the guide,
    section "Integration Reality").

--------------------------------------------------------------------------------
AUTHORIZED USE ONLY
  Run scripted scans/attacks only against networks you own or have explicit
  written authorization to test. "Attack" commands (deauth, beacon spam, etc.)
  are intentionally NOT in the default safe command set and must be enabled by
  the operator who accepts responsibility for them.
--------------------------------------------------------------------------------

DEPENDENCIES
  * Python 3.8+
  * pyserial      pip install pyserial

WIRING / SERIAL ASSUMPTIONS  (verify against your hardware!)
  * Baud rate: Marauder's serial console runs at 115200 by default.
    VERIFY on your build -- some forks differ.
  * ESP32 default console is UART0:  GPIO1 = TX,  GPIO3 = RX.
  * Cross the lines:  ESP32 TX (GPIO1) -> partner RX,  ESP32 RX (GPIO3) <- partner TX.
  * Common ground between the two devices is REQUIRED.
  * Logic level is 3.3 V on BOTH the ESP32 and the Flipper GPIO -- compatible.
    !! NEVER put 5 V on these pins. 5 V can destroy the ESP32 input. !!
  * If you simply plug the ESP32 into USB, the onboard USB-UART bridge exposes
    the same console; pick that port instead of raw GPIO wiring.

USAGE
  # List candidate ports:
  python3 serial_bridge.py --list

  # Interactive console (type Marauder commands, Ctrl-C to quit):
  python3 serial_bridge.py --port /dev/ttyUSB0 --baud 115200 --interactive

  # Run a scripted timed AP scan and save the log:
  python3 serial_bridge.py --port /dev/ttyUSB0 --script scan --duration 20 \
      --log session.log

  # Send a single command and print the reply:
  python3 serial_bridge.py --port /dev/ttyUSB0 --cmd "scanap"
"""

import argparse
import sys
import time
from datetime import datetime

try:
    import serial                       # pyserial
    from serial.tools import list_ports
except ImportError:
    sys.stderr.write(
        "ERROR: pyserial is required. Install it with:  pip install pyserial\n"
    )
    sys.exit(2)


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class MarauderLink:
    def __init__(self, port, baud=115200, log_path=None, timeout=0.2):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.log_path = log_path
        self._log_fh = open(log_path, "a", encoding="utf-8") if log_path else None
        self.ser = None

    # -- lifecycle -----------------------------------------------------------
    def open(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        time.sleep(0.3)  # let the line settle / ESP32 reset on DTR toggle
        self._emit(f"--- opened {self.port} @ {self.baud} ---")
        return self

    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
        self._emit("--- closed ---")
        if self._log_fh:
            self._log_fh.close()

    def __enter__(self):
        return self.open()

    def __exit__(self, *exc):
        self.close()

    # -- io ------------------------------------------------------------------
    def _emit(self, text):
        line = f"[{ts()}] {text}"
        print(line)
        if self._log_fh:
            self._log_fh.write(line + "\n")
            self._log_fh.flush()

    def send(self, cmd):
        self._emit(f">> {cmd}")
        self.ser.write((cmd + "\n").encode("utf-8", errors="replace"))
        self.ser.flush()

    def drain(self, seconds):
        """Read and log everything that arrives for `seconds`."""
        end = time.time() + seconds
        buf = b""
        while time.time() < end:
            chunk = self.ser.read(4096)
            if chunk:
                buf += chunk
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    self._emit("<< " + raw.decode("utf-8", errors="replace").rstrip("\r"))
            else:
                time.sleep(0.02)
        if buf:  # flush trailing partial line
            self._emit("<< " + buf.decode("utf-8", errors="replace").rstrip("\r"))


# -----------------------------------------------------------------------------
# A small, intentionally SAFE default command vocabulary.
# These are discovery/utility commands. Destructive/transmit commands are NOT
# listed here on purpose -- pass them explicitly with --cmd if authorized.
# Command names follow common Marauder console conventions; VERIFY with `help`
# on your firmware version, since command names change between releases.
# -----------------------------------------------------------------------------
SAFE_COMMANDS = {
    "help":      "help",        # list available commands on THIS firmware
    "info":      "info",        # device / firmware info
    "scanap":    "scanap",      # passive AP scan
    "scansta":   "scansta",     # station scan
    "stopscan":  "stopscan",    # stop the running scan
    "list_ap":   "list -a",     # list discovered APs
    "clearlist": "clearlist",   # clear the in-memory list
    "channel":   "channel",     # show/set channel
}

SCRIPTS = {
    # name -> list of (command, wait_seconds)
    "scan": [
        ("help", 1),
        ("scanap", None),     # None duration -> use --duration
        ("stopscan", 1),
        ("list -a", 3),
    ],
    "info": [
        ("info", 2),
    ],
}


def do_list_ports():
    ports = list(list_ports.comports())
    if not ports:
        print("No serial ports found.")
        return
    print("Available serial ports:")
    for p in ports:
        print(f"  {p.device:20} {p.description}")
    print(
        "\nTypical Marauder ports:\n"
        "  Linux : /dev/ttyUSB0  or  /dev/ttyACM0\n"
        "  macOS : /dev/cu.usbserial-*  or  /dev/cu.usbmodem*\n"
        "  Windows: COM3, COM4, ...\n"
    )


def run_script(link, name, duration):
    if name not in SCRIPTS:
        print(f"Unknown script '{name}'. Known: {', '.join(SCRIPTS)}")
        return
    for cmd, wait in SCRIPTS[name]:
        link.send(cmd)
        link.drain(wait if wait is not None else duration)


def interactive(link):
    print("Interactive mode. Type Marauder commands; Ctrl-C to quit.")
    print("Tip: run 'help' first to see commands supported by your firmware.")
    try:
        while True:
            try:
                cmd = input("marauder> ").strip()
            except EOFError:
                break
            if not cmd:
                link.drain(0.3)
                continue
            link.send(cmd)
            link.drain(1.5)
    except KeyboardInterrupt:
        print("\nExiting.")


def main(argv=None):
    ap = argparse.ArgumentParser(description="Flipper<->ESP32 Marauder serial bridge.")
    ap.add_argument("--list", action="store_true", help="list serial ports and exit")
    ap.add_argument("--port", help="serial port (e.g. /dev/ttyUSB0, COM3)")
    ap.add_argument("--baud", type=int, default=115200, help="baud rate (default 115200)")
    ap.add_argument("--log", help="append a timestamped session log to this file")
    ap.add_argument("--interactive", action="store_true", help="interactive console")
    ap.add_argument("--cmd", help="send a single command, print reply, exit")
    ap.add_argument("--script", help=f"run a scripted sequence: {', '.join(SCRIPTS)}")
    ap.add_argument("--duration", type=int, default=15,
                    help="seconds for open-ended scan steps (default 15)")
    args = ap.parse_args(argv)

    if args.list:
        do_list_ports()
        return 0

    if not args.port:
        ap.error("--port is required (or use --list)")

    with MarauderLink(args.port, args.baud, log_path=args.log) as link:
        if args.cmd:
            link.send(args.cmd)
            link.drain(2.0)
        elif args.script:
            run_script(link, args.script, args.duration)
        elif args.interactive:
            interactive(link)
        else:
            print("Nothing to do. Use --interactive, --cmd, or --script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

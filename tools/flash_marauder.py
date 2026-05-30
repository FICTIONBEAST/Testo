#!/usr/bin/env python3
"""
flash_marauder.py  --  Deliverable 4.3
Build / flash automation for ESP32 Marauder, with a step-by-step procedure.

================================================================================
WHAT THIS DOES
  * Helps you identify the serial port the ESP32 is on (Windows/macOS/Linux).
  * Backs up the device's CURRENT flash to a .bin file BEFORE you overwrite it.
  * Flashes a Marauder firmware .bin you supply, via `esptool`.
  * Verifies the flash and reads back the chip identity.
  * Prints the hardware-button "enter download mode" sequence and the two
    supported flashing paths (web flasher vs CLI).

WHAT THIS DOES *NOT* DO
  * It does NOT download firmware for you and it does NOT bundle any firmware.
    You must obtain the correct .bin from the OFFICIAL Marauder source yourself
    and verify its version/integrity. (See the note below.)
  * It does NOT compile Marauder from source; it flashes a prebuilt image. The
    build path is documented in the procedure text for reference only.

--------------------------------------------------------------------------------
AUTHORIZED USE ONLY
  Flash only hardware you own. Marauder is a security-research/educational tool;
  operate the resulting device only against networks you own or are explicitly,
  in writing, authorized to assess.
--------------------------------------------------------------------------------

!!! FIRMWARE SOURCE / VERSION CAVEAT !!!
  Download Marauder firmware ONLY from the official project:
      https://github.com/justcallmekoko/ESP32Marauder   (releases)
      https://justcallmekoko.github.io/ESP32Marauder/    (web flasher)
  Versions, partition layouts and tooling change over time. The values in this
  script (flash offset 0x10000, etc.) are common defaults but you MUST verify
  them against the current official instructions for YOUR board variant before
  flashing. Do not trust any version baked into this guide.

DEPENDENCIES
  * Python 3.8+
  * esptool        pip install esptool
  * pyserial       pip install pyserial   (port enumeration; pulled in by esptool)

USAGE
  # 1) Find the port:
  python3 flash_marauder.py --list-ports

  # 2) Read chip info (confirms wiring + download mode works):
  python3 flash_marauder.py --port /dev/ttyUSB0 --chip-info

  # 3) Back up existing firmware (DO THIS FIRST):
  python3 flash_marauder.py --port /dev/ttyUSB0 --backup backup_4MB.bin --flash-size 4MB

  # 4) Flash a Marauder image you downloaded from the official source:
  python3 flash_marauder.py --port /dev/ttyUSB0 --firmware esp32_marauder.bin \
      --offset 0x10000 --verify

  # 5) Print the manual procedure / button sequence:
  python3 flash_marauder.py --procedure
"""

import argparse
import platform
import shutil
import subprocess
import sys


PROCEDURE = r"""
================================================================================
 MARAUDER FLASHING PROCEDURE  (read fully before starting)
================================================================================

PREREQUISITES / DEPENDENCIES
  * The ESP32 Marauder board and a DATA-capable USB cable (not charge-only).
  * `esptool` installed:  pip install esptool
  * The correct firmware .bin for YOUR board variant, downloaded from the
    OFFICIAL Marauder release page. Verify the version on the device's
    "Device Info" screen after flashing.
  * 3.3 V LOGIC WARNING: the ESP32 is a 3.3 V part. Never feed 5 V into its
    GPIO/UART pins. USB 5 V is fine because the onboard regulator handles it.

--------------------------------------------------------------------------------
STEP 1 -- ENTER FLASH (DOWNLOAD) MODE
--------------------------------------------------------------------------------
  Many ESP32 dev boards auto-enter download mode via the USB-UART chip's
  DTR/RTS lines, so esptool can do it for you. If it cannot, do it by hand
  using the two buttons.

  Button mapping (MOST LIKELY on this hardware -- confirm on yours):
    * BOOT  / IO0  -> the button that only matters WHILE powering on / resetting.
    * RESET / EN   -> the button that reboots the device the instant you press it.

  How to tell them apart safely:
    - Tap a button with the device running. If the screen reboots -> that is
      RESET/EN. If nothing happens -> that is (probably) BOOT/IO0.

  Manual download-mode hold sequence:
    1. Press and HOLD  BOOT (IO0).
    2. While holding BOOT, briefly TAP  RESET (EN).
    3. RELEASE BOOT.
    The chip is now in download mode, waiting for esptool.

  NOTE on silkscreen: the labels `2G4` / `5G` and the `1` / `2` printed next to
  them most likely mark ANTENNA PORTS, not these buttons. Don't confuse antenna
  port numbering with the BOOT/RESET buttons.

--------------------------------------------------------------------------------
STEP 2 -- IDENTIFY THE PORT
--------------------------------------------------------------------------------
  Windows : Device Manager -> Ports (COM & LPT) -> "COM3", "COM5", ...
  macOS   : ls /dev/cu.*        -> /dev/cu.usbserial-XXXX or /dev/cu.usbmodemXXXX
  Linux   : ls /dev/ttyUSB* /dev/ttyACM*   (CP210x/CH34x -> ttyUSB; native USB -> ttyACM)
            You may need to be in the 'dialout' group:  sudo usermod -aG dialout $USER

--------------------------------------------------------------------------------
STEP 3 -- BACK UP CURRENT FIRMWARE (rollback insurance)
--------------------------------------------------------------------------------
  esptool.py --port <PORT> read_flash 0x0 0x400000 backup_4MB.bin
  (0x400000 = 4 MB; use your actual flash size. Keep this file safe -- it lets
   you restore the previous firmware with write_flash 0x0 backup_4MB.bin.)

--------------------------------------------------------------------------------
STEP 4 -- FLASH  (two supported paths)
--------------------------------------------------------------------------------
  PATH A -- WEB FLASHER (easiest):
    1. Open the OFFICIAL Marauder web flasher in Chrome/Edge (WebSerial).
    2. Put the board in download mode (Step 1) if it doesn't auto-enter.
    3. Select the port, pick your board/version, click Install, wait, done.
    (The web flasher is just esptool compiled to WebAssembly behind the scenes.)

  PATH B -- CLI with esptool (full control):
    esptool.py --chip esp32 --port <PORT> --baud 921600 \
        write_flash -z 0x10000 esp32_marauder.bin
    * --chip: use esp32 / esp32s2 / esp32s3 to match YOUR board.
    * 0x10000 is the common app offset for a single combined app image; some
      releases ship separate bootloader/partition/app images at 0x1000/0x8000/
      0x10000. FOLLOW THE OFFICIAL INSTRUCTIONS FOR YOUR RELEASE.

--------------------------------------------------------------------------------
STEP 5 -- VERIFY & BOOT
--------------------------------------------------------------------------------
  * esptool prints "Hash of data verified." on a good write (use --verify).
  * Tap RESET (EN) to boot. The Marauder splash + menu should appear.
  * Open Device Info and confirm the Version matches what you flashed.
  * If it bricks or boot-loops: re-enter download mode and either reflash or
    restore your backup with:  esptool.py --port <PORT> write_flash 0x0 backup_4MB.bin
================================================================================
"""


def esptool_cmd():
    """Return the best way to invoke esptool on this system, or None."""
    if shutil.which("esptool.py"):
        return ["esptool.py"]
    if shutil.which("esptool"):
        return ["esptool"]
    # Fall back to module form; works if installed in the active interpreter.
    return [sys.executable, "-m", "esptool"]


def run(cmd):
    print("[*] " + " ".join(cmd))
    try:
        return subprocess.call(cmd)
    except FileNotFoundError:
        sys.stderr.write(
            "ERROR: esptool not found. Install it with:  pip install esptool\n"
        )
        return 127


def list_ports():
    try:
        from serial.tools import list_ports as lp
    except ImportError:
        sys.stderr.write("pyserial not installed; install with: pip install pyserial\n")
        return 2
    ports = list(lp.comports())
    sysname = platform.system()
    print(f"Detected OS: {sysname}")
    if not ports:
        print("No serial ports found. Plug in the board and check the cable (must be data-capable).")
    else:
        for p in ports:
            print(f"  {p.device:24} {p.description}")
    hints = {
        "Windows": "Look for COMx under Device Manager > Ports.",
        "Darwin":  "Look for /dev/cu.usbserial-* or /dev/cu.usbmodem*.",
        "Linux":   "Look for /dev/ttyUSB* (CP210x/CH34x) or /dev/ttyACM* (native USB).",
    }
    print("Hint:", hints.get(sysname, "Check your platform's serial device naming."))
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description="ESP32 Marauder flash automation.")
    ap.add_argument("--list-ports", action="store_true", help="enumerate serial ports")
    ap.add_argument("--procedure", action="store_true", help="print the manual flashing procedure")
    ap.add_argument("--port", help="serial port (e.g. /dev/ttyUSB0, COM3)")
    ap.add_argument("--chip", default="esp32", help="chip type: esp32 / esp32s2 / esp32s3")
    ap.add_argument("--chip-info", action="store_true", help="read chip id / verify download mode")
    ap.add_argument("--backup", metavar="FILE", help="read current flash to FILE first")
    ap.add_argument("--flash-size", default="4MB", help="flash size for backup (e.g. 4MB)")
    ap.add_argument("--firmware", metavar="FILE", help="Marauder .bin to write")
    ap.add_argument("--offset", default="0x10000", help="flash offset (default 0x10000)")
    ap.add_argument("--baud", default="921600", help="flash baud (default 921600)")
    ap.add_argument("--verify", action="store_true", help="verify after writing")
    args = ap.parse_args(argv)

    if args.procedure:
        print(PROCEDURE)
        return 0
    if args.list_ports:
        return list_ports()

    base = esptool_cmd()

    if args.chip_info:
        if not args.port:
            ap.error("--chip-info needs --port")
        return run(base + ["--chip", args.chip, "--port", args.port, "chip_id"])

    if args.backup:
        if not args.port:
            ap.error("--backup needs --port")
        size_map = {"1MB": "0x100000", "2MB": "0x200000", "4MB": "0x400000",
                    "8MB": "0x800000", "16MB": "0x1000000"}
        size = size_map.get(args.flash_size.upper(), None)
        if size is None:
            ap.error(f"unknown --flash-size {args.flash_size}; use one of {list(size_map)}")
        print(f"[*] Backing up current firmware ({args.flash_size}) -> {args.backup}")
        rc = run(base + ["--chip", args.chip, "--port", args.port,
                         "read_flash", "0x0", size, args.backup])
        if rc != 0:
            sys.stderr.write("Backup failed; refusing to continue.\n")
            return rc

    if args.firmware:
        if not args.port:
            ap.error("--firmware needs --port")
        print("\n!!! Confirm this .bin came from the OFFICIAL Marauder source and "
              "matches your board variant before proceeding. !!!\n")
        cmd = base + ["--chip", args.chip, "--port", args.port, "--baud", args.baud,
                      "write_flash"]
        if args.verify:
            cmd += ["--verify"]
        cmd += ["-z", args.offset, args.firmware]
        rc = run(cmd)
        if rc == 0:
            print("[+] Flash complete. Tap RESET (EN) to boot and check Device Info "
                  "for the expected version.")
        return rc

    ap.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())

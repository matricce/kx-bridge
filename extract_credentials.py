"""
extract_credentials.py – Extracts Anycubic LAN-MQTT credentials from the RAM
of the running AnycubicSlicerNext process.

Requirements:
  - AnycubicSlicerNext is running and connected to the printer
  - Same user account as the slicer process (no admin required)

Usage:
  python3 extract_credentials.py [--write-env] [--env-file ../.env]

How it works:
  1. Find process "AnycubicSlicer.exe" (Windows) or "AnycubicSlicer" (Linux)
  2. Scan memory pages of the process (only r/rw, no exec pages)
  3. Search for MQTT credential patterns:
       Username:  user[A-Za-z0-9]{8,12}
       Password:  [A-Za-z0-9+/]{13,18}
       Printer IP: d{1,3}.d{1,3}.d{1,3}.d{1,3}
  4. Filter candidates by plausibility and print results
  5. Optionally write .env file
"""

import argparse
import os
import re
import struct
import sys
import platform

# ---------------------------------------------------------------------------
# Platform detection
# ---------------------------------------------------------------------------

IS_WINDOWS = platform.system() == "Windows"
IS_LINUX   = platform.system() == "Linux"

# ---------------------------------------------------------------------------
# Patterns
# ---------------------------------------------------------------------------

# Username: "user" + 8–12 alphanumeric characters (printer-generated)
RE_USERNAME = re.compile(rb'user[A-Za-z0-9]{8,12}(?=[^A-Za-z0-9]|$)')

# Password: 13–20 alphanumeric characters (no / since no RTSP path)
# Anycubic passwords: mixed upper/lower/digits, no slash
RE_PASSWORD = re.compile(rb'[A-Za-z0-9]{13,20}(?=[^A-Za-z0-9]|$)')

# Context pattern: password directly following "password" in memory
RE_PASSWORD_CTX = re.compile(rb'(?:password|passwd|Password)\x00{0,4}([A-Za-z0-9]{10,25})(?=[^A-Za-z0-9]|$)', re.IGNORECASE)

# Proximity pattern: username followed by password within close range (<512 bytes)
RE_USER_PASS_PROXIMITY = re.compile(
    rb'(user[A-Za-z0-9]{8,12}).{1,512}?([A-Za-z0-9]{13,20})(?=[^A-Za-z0-9]|$)',
    re.DOTALL
)

# IPv4 address (no localhost, no broadcast)
RE_IP = re.compile(rb'(?<![.\d])(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?![.\d])')

# mode_id: 5-digit number (e.g. 20030)
RE_MODE_ID = re.compile(rb'(?<!\d)(2\d{4})(?!\d)')

# device_id: 32 hex characters (MD5 format)
RE_DEVICE_ID = re.compile(rb'[0-9a-f]{32}(?=[^0-9a-f]|$)')


# ---------------------------------------------------------------------------
# Windows – read memory via ctypes / ReadProcessMemory
# ---------------------------------------------------------------------------

def _win_find_pid(name: str) -> "int | None":
    """Find the PID of a process by name (case-insensitive)."""
    import ctypes
    import ctypes.wintypes

    TH32CS_SNAPPROCESS = 0x00000002

    class PROCESSENTRY32(ctypes.Structure):
        _fields_ = [
            ("dwSize",              ctypes.wintypes.DWORD),
            ("cntUsage",            ctypes.wintypes.DWORD),
            ("th32ProcessID",       ctypes.wintypes.DWORD),
            ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
            ("th32ModuleID",        ctypes.wintypes.DWORD),
            ("cntThreads",          ctypes.wintypes.DWORD),
            ("th32ParentProcessID", ctypes.wintypes.DWORD),
            ("pcPriClassBase",      ctypes.c_long),
            ("dwFlags",             ctypes.wintypes.DWORD),
            ("szExeFile",           ctypes.c_char * 260),
        ]

    snap = ctypes.windll.kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if snap == ctypes.wintypes.HANDLE(-1).value:
        return None

    entry = PROCESSENTRY32()
    entry.dwSize = ctypes.sizeof(PROCESSENTRY32)

    try:
        if not ctypes.windll.kernel32.Process32First(snap, ctypes.byref(entry)):
            return None
        while True:
            if entry.szExeFile.decode("utf-8", errors="replace").lower() == name.lower():
                return entry.th32ProcessID
            if not ctypes.windll.kernel32.Process32Next(snap, ctypes.byref(entry)):
                break
    finally:
        ctypes.windll.kernel32.CloseHandle(snap)
    return None


def _win_read_memory(pid: int, chunk_size: int = 0x10000) -> "list[bytes]":
    """Read all readable memory pages of a Windows process."""
    import ctypes
    import ctypes.wintypes

    PROCESS_VM_READ           = 0x0010
    PROCESS_QUERY_INFORMATION = 0x0400
    MEM_COMMIT    = 0x1000
    PAGE_NOACCESS = 0x01
    PAGE_GUARD    = 0x100

    class MEMORY_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("BaseAddress",       ctypes.c_void_p),
            ("AllocationBase",    ctypes.c_void_p),
            ("AllocationProtect", ctypes.wintypes.DWORD),
            ("RegionSize",        ctypes.c_size_t),
            ("State",             ctypes.wintypes.DWORD),
            ("Protect",           ctypes.wintypes.DWORD),
            ("Type",              ctypes.wintypes.DWORD),
        ]

    k32 = ctypes.windll.kernel32
    handle = k32.OpenProcess(PROCESS_VM_READ | PROCESS_QUERY_INFORMATION, False, pid)
    if not handle:
        raise PermissionError(f"OpenProcess failed (PID {pid}): {ctypes.GetLastError()}")

    chunks = []
    addr = 0
    mbi = MEMORY_BASIC_INFORMATION()

    try:
        while k32.VirtualQueryEx(handle, ctypes.c_void_p(addr),
                                 ctypes.byref(mbi), ctypes.sizeof(mbi)):
            skip = (
                mbi.State != MEM_COMMIT or
                mbi.Protect & PAGE_NOACCESS or
                mbi.Protect & PAGE_GUARD or
                mbi.RegionSize > 256 * 1024 * 1024  # skip >256 MB regions
            )
            if not skip:
                buf = ctypes.create_string_buffer(mbi.RegionSize)
                read = ctypes.c_size_t(0)
                if k32.ReadProcessMemory(handle, ctypes.c_void_p(addr),
                                         buf, mbi.RegionSize, ctypes.byref(read)):
                    chunks.append(bytes(buf[:read.value]))
            addr += mbi.RegionSize
            if addr >= 0x7FFFFFFFFFFF:  # end of user space (64-bit)
                break
    finally:
        k32.CloseHandle(handle)

    return chunks


# ---------------------------------------------------------------------------
# Linux – read memory via /proc/{pid}/mem
# ---------------------------------------------------------------------------

def _linux_find_pid(name: str) -> "int | None":
    """Find PID by process name in /proc."""
    for entry in os.listdir("/proc"):
        if not entry.isdigit():
            continue
        try:
            cmdline = open(f"/proc/{entry}/cmdline", "rb").read()
            if name.lower().encode() in cmdline.lower():
                return int(entry)
        except (PermissionError, FileNotFoundError):
            continue
    return None


def _linux_read_memory(pid: int) -> "list[bytes]":
    """Read readable memory segments from /proc/{pid}/mem."""
    chunks = []
    maps_path = f"/proc/{pid}/maps"
    mem_path  = f"/proc/{pid}/mem"

    try:
        maps = open(maps_path).readlines()
        mem  = open(mem_path, "rb")
    except PermissionError:
        raise PermissionError(
            f"No access to /proc/{pid}/mem — "
            "run the script as the same user as the slicer process."
        )

    for line in maps:
        parts = line.split()
        if len(parts) < 2:
            continue
        perms = parts[1]
        if "r" not in perms:          # readable pages only
            continue
        if "x" in perms:              # skip code pages (no strings)
            continue
        try:
            start, end = [int(x, 16) for x in parts[0].split("-")]
        except ValueError:
            continue
        size = end - start
        if size > 256 * 1024 * 1024:  # skip >256 MB regions
            continue
        try:
            mem.seek(start)
            data = mem.read(size)
            if data:
                chunks.append(data)
        except (OSError, ValueError):
            continue

    mem.close()
    return chunks


# ---------------------------------------------------------------------------
# Pattern search
# ---------------------------------------------------------------------------

def _is_valid_ip(ip_bytes: bytes) -> bool:
    parts = ip_bytes.split(b".")
    if len(parts) != 4:
        return False
    try:
        nums = [int(p) for p in parts]
    except ValueError:
        return False
    if nums[0] in (0, 127, 255):
        return False
    if nums == [0, 0, 0, 0]:
        return False
    return all(0 <= n <= 255 for n in nums)


def search_chunks(chunks: "list[bytes]") -> dict:
    """Search memory chunks for credential patterns."""
    usernames  = {}   # value → count
    passwords  = {}
    ips        = {}
    device_ids = {}

    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if i % 50 == 0 or i == total - 1:
            pct = (i + 1) * 100 // total
            mb_done = sum(len(c) for c in chunks[:i+1]) / 1024 / 1024
            print(f"\r[*] Scanning ... {pct:3d}%  ({mb_done:.0f} MB)", end="", flush=True)
        for m in RE_USERNAME.finditer(chunk):
            v = m.group().decode("ascii", errors="replace")
            usernames[v] = usernames.get(v, 0) + 1

        # Proximity: password within 512 bytes after a username
        for m in RE_USER_PASS_PROXIMITY.finditer(chunk):
            pw = m.group(2).decode("ascii", errors="replace")
            has_upper = any(c.isupper() for c in pw)
            has_lower = any(c.islower() for c in pw)
            has_digit = any(c.isdigit() for c in pw)
            if has_upper and has_lower and has_digit:
                passwords[pw] = passwords.get(pw, 0) + 500

        for m in RE_PASSWORD.finditer(chunk):
            v = m.group().decode("ascii", errors="replace")
            # Filter: at least 2 uppercase + 2 lowercase + 1 digit
            has_upper = sum(1 for c in v if c.isupper()) >= 2
            has_lower = sum(1 for c in v if c.islower()) >= 2
            has_digit = sum(1 for c in v if c.isdigit()) >= 1
            if has_upper and has_lower and has_digit:
                passwords[v] = passwords.get(v, 0) + 1

        for m in RE_IP.finditer(chunk):
            ip = m.group(1)
            if _is_valid_ip(ip):
                v = ip.decode("ascii")
                ips[v] = ips.get(v, 0) + 1

        for m in RE_DEVICE_ID.finditer(chunk):
            v = m.group().decode("ascii")
            device_ids[v] = device_ids.get(v, 0) + 1

    print()  # newline after progress line

    # Sort by frequency, most frequent first
    def top(d, n=10):
        return sorted(d.items(), key=lambda x: -x[1])[:n]

    return {
        "usernames":  top(usernames),
        "passwords":  top(passwords),
        "ips":        top(ips, 10),
        "device_ids": top(device_ids),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

SLICER_NAMES = [
    "AnycubicSlicerNext.exe",  # Windows
    "AnycubicSlicer.exe",
    "AnycubicSlicerNext",      # Linux
    "AnycubicSlicer",
]


def find_slicer_pid() -> "tuple[int, str] | tuple[None, None]":
    for name in SLICER_NAMES:
        if IS_WINDOWS:
            pid = _win_find_pid(name)
        else:
            pid = _linux_find_pid(name)
        if pid:
            return pid, name
    return None, None


def read_process(pid: int) -> "list[bytes]":
    if IS_WINDOWS:
        return _win_read_memory(pid)
    else:
        return _linux_read_memory(pid)


def write_env(results: dict, env_path: str,
              username: str, password: str, ip: str,
              mode_id: str = "20030", device_id: str = ""):
    lines = []
    if os.path.isfile(env_path):
        with open(env_path) as f:
            lines = f.readlines()

    def set_val(key, val):
        nonlocal lines
        for i, line in enumerate(lines):
            if line.startswith(f"{key}="):
                lines[i] = f"{key}={val}\n"
                return
        lines.append(f"{key}={val}\n")

    set_val("PRINTER_IP",    ip)
    set_val("MQTT_USERNAME", username)
    set_val("MQTT_PASSWORD", password)
    if device_id:
        set_val("DEVICE_ID", device_id)
    if mode_id:
        set_val("MODE_ID", mode_id)

    with open(env_path, "w") as f:
        f.writelines(lines)
    print(f"\n✓ Credentials saved to '{env_path}'.")


def main():
    parser = argparse.ArgumentParser(
        description="Extract MQTT credentials from the AnycubicSlicer process RAM"
    )
    parser.add_argument("--write-env",  action="store_true",
                        help="Write found credentials to .env file")
    parser.add_argument("--env-file",   default=None,
                        help="Path to .env file (default: ../.env relative to this script)")
    parser.add_argument("--pid",        type=int, default=None,
                        help="Specify process PID directly (skips auto-detection)")
    parser.add_argument("--verbose",    action="store_true",
                        help="Show all candidates, not just the best match")
    args = parser.parse_args()

    # Determine .env path
    if args.env_file:
        env_path = args.env_file
    else:
        env_path = os.path.join(os.path.dirname(__file__), "..", ".env")
        env_path = os.path.normpath(env_path)

    # Find process
    if args.pid:
        pid, proc_name = args.pid, f"PID {args.pid}"
    else:
        print("[*] Searching for AnycubicSlicer process ...")
        pid, proc_name = find_slicer_pid()
        if not pid:
            print("✗ AnycubicSlicer not found. Please start the slicer, connect it "
                  "to the printer, then run this script again.")
            sys.exit(1)

    print(f"[*] Process found: {proc_name} (PID {pid})")
    print(f"[*] Reading process memory ...")

    try:
        chunks = read_process(pid)
    except PermissionError as e:
        print(f"✗ Permission error: {e}")
        sys.exit(1)

    total_mb = sum(len(c) for c in chunks) / 1024 / 1024
    print(f"[*] {len(chunks)} memory segments read ({total_mb:.1f} MB)")
    print(f"[*] Searching for credentials ...")

    results = search_chunks(chunks)

    # Output
    print("\n" + "="*55)
    print("  RESULTS")
    print("="*55)

    def show(label, items, verbose):
        if not items:
            print(f"  {label:12s}  —  not found")
            return items[0][0] if items else ""
        best = items[0][0]
        print(f"  {label:12s}  {best}  (matches: {items[0][1]})")
        if verbose and len(items) > 1:
            for val, cnt in items[1:]:
                print(f"  {'':12s}  {val}  (matches: {cnt})")
        return best

    best_user   = show("Username",   results["usernames"],  args.verbose)
    best_pass   = show("Password",   results["passwords"],  args.verbose)
    best_device = show("Device-ID",  results["device_ids"], args.verbose)

    # IP: prefer 192.168.x.x
    lan_ips = [(ip, cnt) for ip, cnt in results["ips"]
               if ip.startswith("192.168.") or ip.startswith("10.") or ip.startswith("172.")]
    if not lan_ips:
        lan_ips = results["ips"]
    best_ip = show("Printer IP",  lan_ips, args.verbose)

    print("="*55)

    if not best_user or not best_pass:
        print("\n⚠  No complete credentials found.")
        print("   Make sure the slicer is connected to the printer.")
        sys.exit(1)

    if args.write_env:
        write_env(results, env_path, best_user, best_pass, best_ip,
                  device_id=best_device)
    else:
        print(f"\nTip: pass --write-env to save credentials to '{env_path}'.")


if __name__ == "__main__":
    main()

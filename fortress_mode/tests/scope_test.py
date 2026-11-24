"""Catches a local helper used before its definition, which Lua reads as a missing global and the game as a fatal error.

Run: python3 tests/scope_test.py   (needs luac 5.3 or newer)
"""
import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parent.parent / "assets" / "scar" / "winconditions" / "fortress_mode.scar"
source = SCRIPT.read_text()
locals_ = set(re.findall(r"^local function (\w+)", source, re.M)) | set(re.findall(r"^local (\w+)\s*=", source, re.M))
listing = subprocess.run(["luac", "-l", "-l", "-p", str(SCRIPT)], capture_output=True, text=True, check=True).stdout
misses = sorted({(int(line), name) for line, name in re.findall(r"\[(\d+)\]\s+[GS]ETTABUP\s.*_ENV \"(\w+)\"", listing) if name in locals_})
for line, name in misses:
    print(f"FAIL line {line}: {name} is a local defined later, read here as a global")
print("ALL OK" if not misses else f"FAILED {len(misses)}")
raise SystemExit(len(misses))

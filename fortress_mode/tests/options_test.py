"""Every lobby choice in tools/gen_mod.py must be readable by the script.

Run: python3 tests/options_test.py
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location("gen_mod", ROOT / "tools" / "gen_mod.py")
gen_mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen_mod)
script = (ROOT / "assets" / "scar" / "winconditions" / "fortress_mode.scar").read_text()

numeric = dict(re.findall(r'ReadNumber\(section, "(\w+)", "(\w+)"', script))
enums = set(re.findall(r'ReadEnum\(section, "(\w+)"', script))
failed = 0
for option in gen_mod.OPTIONS:
    key, default, items = option[0], option[5], option[6]
    if key in numeric:
        prefix = numeric[key]
        bad = [k for k, _ in items if not re.fullmatch(prefix + r"_(off|\d+)", k)]
    elif key in enums:
        bad = []
    else:
        bad = ["not read by the script"]
    if default not in [k for k, _ in items]:
        bad.append(f"default {default} is not a choice")
    print(("FAIL " if bad else "PASS ") + key + (f": {bad}" if bad else ""))
    failed += bool(bad)
print("ALL OK" if failed == 0 else f"FAILED {failed}")
raise SystemExit(failed)

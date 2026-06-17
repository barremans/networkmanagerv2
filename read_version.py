# read_version.py - intern hulpscript voor build.bat
# Leest __version__ uit app/version.py en schrijft naar het pad in argv[1]
import importlib.util, sys, re
from pathlib import Path

out_path = sys.argv[1] if len(sys.argv) > 1 else "version_out.txt"
p = Path("app/version.py")
v = "0.0.0"
try:
    spec = importlib.util.spec_from_file_location("ver", p)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    v = str(getattr(m, "__version__", "0.0.0"))
except Exception:
    t = p.read_text(encoding="utf-8")
    mm = re.search(r'__version__\s*=\s*["\']([0-9]+(?:\.[0-9]+){1,2})["\']', t)
    v = mm.group(1) if mm else "0.0.0"

Path(out_path).write_text(v.strip(), encoding="utf-8")
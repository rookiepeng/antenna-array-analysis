"""
Build script: freezes src/python/bridge.py into a standalone directory
using PyInstaller (--onedir mode).  All native DLLs (numpy, scipy) sit
next to the executable so Windows can load them reliably.

Output:
  dist/bridge/bridge.exe        (Windows)
  dist/bridge/bridge            (Linux / macOS)

Usage:
  python scripts/build_bridge.py
"""

import subprocess
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIDGE_SCRIPT = ROOT / "src" / "python" / "bridge.py"
ARRAYBEAM_PKG = ROOT / "src" / "arraybeam"
SRC_DIR = ROOT / "src"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "pyinstaller"

def main() -> None:
    if not BRIDGE_SCRIPT.exists():
        print(f"ERROR: bridge script not found at {BRIDGE_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    if not ARRAYBEAM_PKG.exists():
        print(f"ERROR: arraybeam package not found at {ARRAYBEAM_PKG}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        sys.executable, "-m", "PyInstaller",
        # --onedir keeps all DLLs next to the executable, which avoids the
        # Windows DLL-load-from-temp-directory failure seen with --onefile.
        "--onedir",
        "--name", "bridge",
        "--distpath", str(DIST_DIR),
        "--workpath", str(BUILD_DIR),
        "--specpath", str(ROOT / "build"),
        # src/arraybeam is on the path so PyInstaller can find the package.
        f"--paths={ARRAYBEAM_PKG}",
        # Explicit hidden imports for arraybeam modules
        "--hidden-import", "arraybeam",
        "--hidden-import", "arraybeam.antenna_array",
        "--hidden-import", "arraybeam.uniform_linear_array",
        "--hidden-import", "arraybeam.uniform_rectangular_array",
        "--hidden-import", "numpy.core._multiarray_umath",
        # Collect all scipy/numpy sub-modules (their native extensions are
        # often missed by static analysis)
        "--collect-all", "scipy",
        "--collect-all", "numpy",
        "--noconfirm",
        str(BRIDGE_SCRIPT),
    ]

    print("Building bridge executable with PyInstaller...")
    print("Command:", " ".join(str(a) for a in cmd))
    print()

    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"\nERROR: PyInstaller failed with exit code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)

    ext = ".exe" if sys.platform == "win32" else ""
    output = DIST_DIR / "bridge" / f"bridge{ext}"
    print(f"\nBuild complete!")
    print(f"  Executable : {output}")
    print(f"\nNext step: run  npm run dist  to package the Electron app.")


if __name__ == "__main__":
    main()

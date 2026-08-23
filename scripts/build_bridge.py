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

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BRIDGE_SCRIPT = ROOT / "src" / "python" / "bridge.py"
# The submodule root; the importable package lives one level below it.
ARRAYBEAM_ROOT = ROOT / "src" / "arraybeam"
ARRAYBEAM_PKG = ARRAYBEAM_ROOT / "arraybeam"
DIST_DIR = ROOT / "dist"
BUILD_DIR = ROOT / "build" / "pyinstaller"

# The bridge relies on the arraybeam 2.x API.
ARRAYBEAM_MIN_MAJOR = 2


def check_arraybeam() -> None:
    """Verify the submodule is checked out and new enough for the bridge."""
    init_py = ARRAYBEAM_PKG / "__init__.py"
    if not init_py.exists():
        print(
            f"ERROR: arraybeam package not found at {ARRAYBEAM_PKG}\n"
            "       Run 'git submodule update --init' first.",
            file=sys.stderr,
        )
        sys.exit(1)

    match = re.search(
        r"^__version__\s*=\s*['\"]([^'\"]+)['\"]",
        init_py.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    if match is None:
        print(f"WARNING: could not read arraybeam version from {init_py}", file=sys.stderr)
        return

    version = match.group(1)
    if int(version.split(".")[0]) < ARRAYBEAM_MIN_MAJOR:
        print(
            f"ERROR: arraybeam {version} is too old; "
            f"the bridge requires {ARRAYBEAM_MIN_MAJOR}.x\n"
            "       Run 'git submodule update --init' to fetch the pinned commit.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Using arraybeam {version} from {ARRAYBEAM_ROOT}")


def main() -> None:
    if not BRIDGE_SCRIPT.exists():
        print(f"ERROR: bridge script not found at {BRIDGE_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    check_arraybeam()

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
        f"--paths={ARRAYBEAM_ROOT}",
        # Explicit hidden imports for arraybeam modules
        "--hidden-import", "arraybeam",
        "--hidden-import", "arraybeam.antenna_array",
        "--hidden-import", "arraybeam.uniform_linear_array",
        "--hidden-import", "arraybeam.uniform_rectangular_array",
        # arraybeam 2.x annotates its public API with numpy.typing.
        "--hidden-import", "numpy.typing",
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

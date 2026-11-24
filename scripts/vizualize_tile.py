#!/usr/bin/env python3
"""Visual inspection of Sentinel-2 GeoTIFFs.

Renders a band combination with `gdal_translate` and shows it in a resizable OpenCV window:

    uv run scripts/vizualize_tile.py resources/download_images/

    left / right   previous / next file in the folder
    up / down      previous / next band combination
    q or escape    quit

Needs `opencv-python` (not the headless build) and a reachable display, so inside the
devcontainer run `xhost +local:` on the host first.
"""

import argparse
import json
import os
import re
import shutil
import socket
import struct
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import cv2

# Band positions follow the merge order of marine_litter.zip_processing, which globs "B*.tif"
# and sorts lexicographically, so B11/B12 land on 10/11 and B8A ends up last:
#   1=B01  2=B02  3=B03  4=B04  5=B05  6=B06  7=B07  8=B08  9=B09  10=B11  11=B12  12=B8A
COMBOS: list[tuple[str, tuple[int, ...]]] = [
    ("true colour B04/B03/B02", (4, 3, 2)),
    ("false colour B08/B04/B03", (8, 4, 3)),
    ("SWIR B12/B08/B04", (11, 8, 4)),
]

# Sentinel-2 L2A reflectance is scaled by 10000; clipping at 3000 keeps water detail visible.
REFLECTANCE_CLIP = 3000

# cv2.waitKeyEx returns platform-specific codes for the arrow keys, so accept the Linux set,
# the Windows set and WASD.
PREV_FILE = {65361, 2424832, ord("a")}
NEXT_FILE = {65363, 2555904, ord("d")}
PREV_COMBO = {65362, 2490368, ord("w")}
NEXT_COMBO = {65364, 2621440, ord("s")}
QUIT = {27, ord("q")}

WINDOW = "tile viewer"

# An X11 connection setup asking for protocol 11.0 and offering no credentials, see
# https://www.x.org/releases/current/doc/xproto/x11protocol.html#Encoding::Connection_Setup
X11_SETUP = struct.pack("<BBHHHH2x", 0x6C, 0, 11, 0, 0, 0)
X11_SUCCESS = b"\x01"


def display_problem() -> str | None:
    """Return why Qt could not open a window, or None to let it try.

    Qt calls abort() when it cannot reach the display, which would kill the interpreter without an
    explanation, so probe the server beforehand. The probe offers no credentials and is therefore
    only conclusive while there is no authority file that Qt could authenticate with.
    """
    display = os.environ.get("DISPLAY", "")
    if not display:
        return "DISPLAY is not set"
    authority = os.environ.get("XAUTHORITY") or Path.home() / ".Xauthority"
    if not re.fullmatch(r":\d+(\.\d+)?", display) or Path(authority).exists():
        return None

    try:
        with socket.socket(socket.AF_UNIX) as probe:
            probe.settimeout(2)
            probe.connect(f"/tmp/.X11-unix/X{display.removeprefix(':').split('.')[0]}")
            probe.sendall(X11_SETUP)
            accepted = probe.recv(8)[:1] == X11_SUCCESS
    except OSError as error:
        return f"no X server reachable on DISPLAY={display} ({error})"
    return None if accepted else f"the X server on DISPLAY={display} refuses unauthorised clients"


def gdalinfo(src: Path, *flags: str) -> dict[str, Any]:
    """Return `gdalinfo` metadata for `src`. The CLI avoids the osgeo/NumPy ABI mismatch in the venv."""
    report = subprocess.run(["gdalinfo", "-json", *flags, str(src)], check=True, capture_output=True, text=True)
    return json.loads(report.stdout)


def render(src: Path, bands: tuple[int, ...], width: int, cache: Path) -> Path:
    """Return an 8-bit PNG of `src` showing `bands`, rendering it into `cache` on first use."""
    info = gdalinfo(src)
    if len(info["bands"]) < max(bands):
        bands = (1,)  # masks and other single-band products have no colour combination

    png = cache / f"{src.stem}__{'_'.join(str(b) for b in bands)}.png"
    if png.exists():
        return png

    command = ["gdal_translate", "-q", "-of", "PNG", "-ot", "Byte", "-outsize", str(width), "0"]
    for band in bands:
        command += ["-b", str(band)]
    if len(bands) == 1:
        # A nodata of 0 hides the low end from GDAL's own statistics, which would render a 0/1
        # mask entirely black, so anchor the range at zero and only take the maximum from the data.
        top = gdalinfo(src, "-mm")["bands"][0].get("computedMax") or 1
        command += ["-scale", "0", str(top), "0", "255"]
    elif info["bands"][0]["type"] != "Byte":
        command += ["-scale", "0", str(REFLECTANCE_CLIP), "0", "255"]
    subprocess.run([*command, str(src), str(png)], check=True)
    return png


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("path", type=Path, help="a GeoTIFF, or a folder of them")
    parser.add_argument("--width", type=int, default=1200, help="render width in pixels (default: %(default)s)")
    args = parser.parse_args()

    problem = display_problem()
    if problem:
        raise SystemExit(
            f"{problem}.\nThe devcontainer gets the host's X socket forwarded, but not the "
            "authorisation for it, so run 'xhost +local:' on the host and try again "
            "(or run this script on the host)."
        )

    folder = args.path if args.path.is_dir() else args.path.parent
    files = sorted(folder.glob("*.tif"))
    if not files:
        raise SystemExit(f"no .tif files in '{folder}'")
    index = files.index(args.path) if args.path in files else 0
    combo = 0

    cache = Path(tempfile.mkdtemp(prefix="vizualize_tile_"))
    try:
        cv2.namedWindow(WINDOW, cv2.WINDOW_NORMAL)
        while True:
            label, bands = COMBOS[combo]
            png = render(files[index], bands, args.width, cache)
            image = cv2.imread(str(png))
            if image is None:
                raise SystemExit(f"could not read the rendered preview '{png}'")
            cv2.setWindowTitle(WINDOW, f"[{index + 1}/{len(files)}] {files[index].name} | {label}")
            cv2.imshow(WINDOW, image)

            key = cv2.waitKeyEx(0)
            if key in QUIT or cv2.getWindowProperty(WINDOW, cv2.WND_PROP_VISIBLE) < 1:
                break
            if key in NEXT_FILE:
                index = (index + 1) % len(files)
            elif key in PREV_FILE:
                index = (index - 1) % len(files)
            elif key in NEXT_COMBO:
                combo = (combo + 1) % len(COMBOS)
            elif key in PREV_COMBO:
                combo = (combo - 1) % len(COMBOS)
    finally:
        cv2.destroyAllWindows()
        shutil.rmtree(cache, ignore_errors=True)


if __name__ == "__main__":
    main()

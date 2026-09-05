#!/usr/bin/env python3
"""Turn raw/img/ exports into the AVIF and WebP files the page actually ships.

Run by hand, never at deploy time: the deploy is a file copy, and the outputs
of this script are committed. That is the whole build system.

    python -m pip install "pillow>=10" pillow-avif-plugin
    python tools/optimize.py                    # every file in raw/img/
    python tools/optimize.py hero.png           # just one
    python tools/optimize.py hero.png --widths 375,1280,1920

For each source it writes campaign/assets/<name>-<width>.avif and .webp. A
source with no --widths is written once at its own size, without a width
suffix. Pass --out to write somewhere else.

campaign/assets/ and not assets/img/, on purpose: assets/img/ holds the brand
-- the logo, the payment marks, the flags, the icons -- and is identical in
every campaign. Everything a campaign generates is its own and belongs in the
slot that gets replaced.

Why both formats: AVIF is roughly a fifth the size at the same quality, and
WebP is the fallback for the browsers that do not have it. In the markup put
the AVIF <source> first and the widest media query first -- first match wins,
and reversing it downloads the 375px crop to every desktop.

Transparency is flattened onto the page background rather than kept: an alpha
channel costs more than the edge it buys on a hero that sits on a solid stage.
Pass --keep-alpha for art that genuinely needs it.

NEVER ship the Figma PNG. One 1.7 MB export became a 23 KB AVIF in the landing
this is taken from.
"""

import argparse
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "img"
OUT = ROOT / "campaign" / "assets"

# --navy-950, the page behind the stage. Alpha is flattened onto this so an
# edge never shows a grey or a white halo.
BACKDROP = (4, 4, 18)

AVIF_QUALITY = 50
WEBP_QUALITY = 80
SOURCES = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}


def load():
    try:
        from PIL import Image
    except ImportError:
        print('optimize: pillow is not installed.\n'
              '  python -m pip install "pillow>=10" pillow-avif-plugin', file=sys.stderr)
        raise SystemExit(1)
    try:
        import pillow_avif  # noqa: F401  -- registers the AVIF plugin with Pillow
    except ImportError:
        print("optimize: pillow-avif-plugin is not installed; AVIF will be skipped.\n"
              "  python -m pip install pillow-avif-plugin", file=sys.stderr)
    return Image


def convert(Image, src: Path, widths, keep_alpha: bool) -> int:
    img = Image.open(src)
    if not keep_alpha and img.mode in ("RGBA", "LA", "P"):
        flat = Image.new("RGB", img.size, BACKDROP)
        rgba = img.convert("RGBA")
        flat.paste(rgba, mask=rgba.split()[-1])
        img = flat
    else:
        img = img.convert("RGBA" if keep_alpha else "RGB")

    OUT.mkdir(parents=True, exist_ok=True)
    written = 0

    for width in widths or [None]:
        frame = img
        suffix = ""
        if width and width < img.width:
            height = round(img.height * width / img.width)
            frame = img.resize((width, height), Image.LANCZOS)
            suffix = f"-{width}"
        elif width:
            suffix = f"-{width}"

        for ext, kwargs in (("avif", {"quality": AVIF_QUALITY}),
                            ("webp", {"quality": WEBP_QUALITY, "method": 6})):
            target = OUT / f"{src.stem}{suffix}.{ext}"
            try:
                frame.save(target, **kwargs)
            except (OSError, KeyError, ValueError) as exc:
                print(f"  {target.name}: skipped ({exc})")
                continue
            print(f"  {target.name}  {target.stat().st_size // 1024} KB")
            written += 1

    return written


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("names", nargs="*", help="file names inside raw/img/ (default: all)")
    ap.add_argument("--widths", default="", help="comma-separated output widths")
    ap.add_argument("--keep-alpha", action="store_true", help="do not flatten transparency")
    ap.add_argument("--out", default="", help="output directory (default: campaign/assets)")
    args = ap.parse_args()

    Image = load()

    global OUT
    if args.out:
        OUT = (ROOT / args.out).resolve()

    if not RAW.is_dir():
        print(f"optimize: {RAW.relative_to(ROOT).as_posix()} does not exist. "
              "Put the Figma exports there; it is gitignored on purpose.")
        return 1

    widths = [int(w) for w in args.widths.split(",") if w.strip()]
    files = ([RAW / n for n in args.names] if args.names
             else sorted(p for p in RAW.iterdir() if p.suffix.lower() in SOURCES))

    if not files:
        print(f"optimize: nothing to do, {RAW.relative_to(ROOT).as_posix()} is empty")
        return 0

    total = 0
    for src in files:
        if not src.is_file():
            print(f"optimize: no such file: {src}", file=sys.stderr)
            return 1
        print(f"{src.name}  {src.stat().st_size // 1024} KB")
        total += convert(Image, src, widths, args.keep_alpha)

    print(f"\noptimize: wrote {total} file(s) into {OUT.relative_to(ROOT).as_posix()}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())

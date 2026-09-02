#!/usr/bin/env python3
"""
Turn the raw Figma exports in raw/img/ into the web assets in assets/img/.

Run by hand, from the project root:

    python tools/optimize.py

This is NOT a build step. The published site never touches raw/ or tools/.
The raw exports are kept so a designer can re-crop later without going back
to a Figma link that has expired. Re-run this only when raw/img/ changes.

Needs Pillow with WebP and AVIF support:

    python -m pip install --upgrade Pillow
"""

from pathlib import Path
import shutil
import sys

from PIL import Image, ImageFilter, features

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "raw" / "img"
OUT = ROOT / "assets" / "img"
ICONS = OUT / "icons"

# The page background. Any transparency in a Figma export is flattened onto
# this so the encoders never have to carry an alpha channel.
PAGE_BG = (0, 0, 46)

# Quality settings. AVIF is far kinder to the dark smooth gradients in the
# hero than WebP is, so it can afford a much lower number for the same look.
AVIF_Q = 50
WEBP_Q = 80

# SVGs that are copied through untouched.
SVG_PASSTHROUGH = {
    "logo-topwin.svg": OUT,
    "card-back-art.svg": OUT,
    "icon-eye.svg": ICONS,
    "flag-ua.svg": ICONS,
    "icon-check.svg": ICONS,
    "social-telegram.svg": ICONS,
    "social-youtube.svg": ICONS,
    "social-tiktok.svg": ICONS,
    "social-instagram.svg": ICONS,
    "social-facebook.svg": ICONS,
    "pay-visa.svg": ICONS,
    "pay-mastercard.svg": ICONS,
    "pay-tether.svg": ICONS,
    "pay-bitcoin.svg": ICONS,
}

# Two entries above are not plain Figma exports. flag-ua.svg is not an export
# at all: it stands in for the emoji Windows cannot draw. icon-eye.svg is an
# export plus the pupil, which the exporter drops. Both are explained in the
# README, section 7.

# raw/img/card-glow.svg and raw/img/card-sphere.svg are deliberately NOT
# copied. Both sit above the card's top edge inside a clipped container, so
# they render as nothing. Verified against the Figma render of node 12:287.


def flatten(im: Image.Image) -> Image.Image:
    """Drop the alpha channel onto the page background."""
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        bg = Image.new("RGB", im.size, PAGE_BG)
        bg.paste(im, mask=im.split()[-1])
        return bg
    return im.convert("RGB")


def kb(path: Path) -> str:
    return f"{path.stat().st_size / 1024:6.1f} KB"


def write_pair(im: Image.Image, stem: str) -> None:
    """Write one image as both AVIF and WebP."""
    avif = OUT / f"{stem}.avif"
    webp = OUT / f"{stem}.webp"
    im.save(avif, format="AVIF", quality=AVIF_Q)
    im.save(webp, format="WEBP", quality=WEBP_Q, method=6)
    print(f"  {avif.name:<24} {kb(avif)}")
    print(f"  {webp.name:<24} {kb(webp)}")


def build_hero() -> None:
    print("hero")
    src = flatten(Image.open(RAW / "hero-desktop.png"))
    # 1920 is the native export width. Never upscale past it.
    for width in (1280, 1920):
        if width > src.width:
            continue
        h = round(src.height * width / src.width)
        write_pair(src.resize((width, h), Image.LANCZOS), f"hero-{width}")

    mob = flatten(Image.open(RAW / "hero-mobile.png"))
    write_pair(mob, f"hero-m-{mob.width}")
    if mob.width < 750:
        print(
            f"  note: the mobile hero is only {mob.width}px wide. Figma will not\n"
            "        render a node above its natural size, so there is no 2x cut.\n"
            "        The scene is soft and glowing, so this is hard to see. For a\n"
            "        sharper retina version, export node 12:311 from Figma at 2x,\n"
            "        save it as raw/img/hero-mobile@2x.png and extend this script."
        )


def build_card_back() -> None:
    """
    The design blurs this photo by 2px behind a 365x488 frame.

    Do not "fix" the softness by dropping the blur. Figma's render of the
    symbol on its own (node 12:283) IS sharp, because the blur lives above it
    and is not part of an isolated node render -- but the composed 1920 frame
    (12:320) shows it. Fitting a Gaussian to that frame lands on 2.0 in the
    365px frame's units, which is what the line below reproduces: sweeping the
    radius against the crop inside card 1 bottoms out at 1.3px on screen
    (mean 3.45 against 4.81 unblurred and 5.24 at twice the radius).

    The blur is baked in here rather than done with a CSS filter. A CSS filter
    on an element that is rotated in 3D, nine times over, forces a filter pass
    per card per frame, and Safari has a long-standing bug where a rounded
    clip leaks square corners around a blurred child. Baking it costs nothing
    at runtime and compresses far better, because the blur has already thrown
    away the high frequencies the encoder would otherwise have to store.
    """
    print("card back")
    src = Image.open(RAW / "card-back-photo.png")

    # Target 2x the largest on-screen size: 365 design px * 0.6487 desktop
    # scale * 2 for retina is 473, rounded up to 480.
    target_w = 480
    target_h = round(target_w * 488 / 365)  # keep the design's 365:488 frame
    im = flatten(src).resize((target_w, target_h), Image.LANCZOS)

    # The design's 2px blur is measured at 365px wide, so scale it up with the
    # image.
    radius = 2.0 * target_w / 365
    im = im.filter(ImageFilter.GaussianBlur(radius=radius))

    out = OUT / "card-back.webp"
    im.save(out, format="WEBP", quality=WEBP_Q, method=6)
    print(f"  {out.name:<24} {kb(out)}  ({target_w}x{target_h}, blur {radius:.2f}px)")


def copy_svgs() -> None:
    print("svg")
    for name, dest in SVG_PASSTHROUGH.items():
        src = RAW / name
        if not src.exists():
            print(f"  MISSING {name}")
            continue
        dest.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest / name)
    print(f"  copied {len(SVG_PASSTHROUGH)} files")


def main() -> int:
    if not features.check("webp"):
        print("Pillow has no WebP support. Reinstall it.", file=sys.stderr)
        return 1
    if not features.check("avif"):
        print("Pillow has no AVIF support. Reinstall it.", file=sys.stderr)
        return 1
    if not RAW.exists():
        print(f"No raw exports at {RAW}", file=sys.stderr)
        return 1

    OUT.mkdir(parents=True, exist_ok=True)
    ICONS.mkdir(parents=True, exist_ok=True)

    build_hero()
    build_card_back()
    copy_svgs()

    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"\nassets/img total: {total / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

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

from PIL import Image, features

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


def build_card_faces() -> None:
    """
    The three card faces are supplied as finished art, authored at exactly
    twice the 272x381 card of the design:

        closed_card.png   the back everyone sees first (TW logo, coins)
        simple_card.png   the revealed face of a 100% / 250% card
        winning_card.png  the revealed face of a 650% card (orange outline)

    Each 640x858 export carries its own baked drop shadow around a 544x762
    card body at (48, 40). The shadow is cropped away, NOT kept: the page
    already casts the card's shadow from CSS (see styles.css section 7), and
    it has to stay there because it changes on hover and must not rotate with
    the flip.

    Alpha is kept so the rounded corners composite cleanly over the page
    gradient. The corner radius in the art is 88px, which is the design's
    44 card units at this 2x scale -- the same radius styles.css clips to.
    """
    print("card faces")
    body = (48, 40, 592, 802)  # 544x762 = 272x381 at 2x, measured from alpha
    for name in ("closed_card", "simple_card", "winning_card"):
        im = Image.open(RAW / f"{name}.png").convert("RGBA").crop(body)
        out = OUT / f"{name}.webp"
        im.save(out, format="WEBP", quality=WEBP_Q, method=6)
        print(f"  {out.name:<24} {kb(out)}  ({im.width}x{im.height})")


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
    build_card_faces()
    copy_svgs()

    total = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file())
    print(f"\nassets/img total: {total / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

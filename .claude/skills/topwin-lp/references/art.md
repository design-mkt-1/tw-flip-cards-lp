# Art

Read this only when generating or preparing imagery. Distilled from
`tw-penalty/docs/ART.md`, which is the full worked example.

## The method

Generate at high resolution on a flat, uniform, featureless **mid-grey**
background, then key the background out with a flood from the frame edge. The
grey is not a style choice: an edge flood keeps every saturated or bright pixel,
so an orange kit, navy trim and white boots all survive while grey *inside* the
figure does not get eaten.

The flood has one blind spot and poses find it. A hand on a hip closes a
triangle between the arm and the body, and that backdrop has no path to the
frame edge — so it stays opaque and the sprite carries a mid-grey hole.
Invisible against the grey render; a grey blob on a dark stage. It cost 6.7% of
one pose and 3.1% of another before an enclosed-pocket pass existed. Check any
pose where a limb closes a loop.

**Generate the first pose from text alone, then pass it back as an image
reference for every other pose**, with the prompt opening on what must not
change — same face, same build, same kit, same rendering style and lighting,
and a CAMERA block naming the reference's lens, distance and eye level. The
reference holds the camera by itself: measured across poses, the feet line sat
at .934/.935/.934 of the canvas and the figure spanned .856/.858. That is
inside a thousandth, and no normalisation pass was needed.

**Two variants per pose, not one.** Picking is free next to regenerating.

**Model identity is a trap.** Two services can both carry a model family and
name the tiers the other way round; getting it wrong does not fail loudly, it
returns a perfectly good render on a different treatment from the nine sprites
beside it. Record the exact model id and the job id for every keeper render.

## Framing discipline

- **Ask for one number, not three.** In a 3:2 frame, a subject spanning a
  quarter of the width forces its height on its own. Ask for the quarter and
  the rest follows; ask for three ratios and they fight.
- **Ask for the shape, not the adjective.** "A full-stretch HIGH flying save"
  came back nearly horizontal at .498 of the canvas against the .830 wanted.
  Naming the geometry — a steep diagonal at roughly 45 degrees, gloves towards
  the top-right corner, boots towards the bottom-left, spanning most of the
  frame's height as well as its width — got .760 on the next attempt.
- **State a contrast requirement as brightness, and name the zone it applies
  to.** "No advertising boards" did not remove a lit orange hoarding through
  the goal mouth. Two rounds went on that. Saying the whole horizontal zone
  stays dark did.
- **Say what is absent.** "No text, no logos, no watermark" does not cover a
  prop the model reasonably infers. A diving goalkeeper came back holding a
  football because nothing forbade one. Every pose prompt now says the hands are
  empty in a sentence of its own.
- **"No floor, no cast shadow" is not always obeyed** on a kneeling or grounded
  pose. Keyable, but the first thing to check on a regeneration.

## Measure, do not eyeball

Every one of these breaks silently — the image stays valid, the layout stays
valid, and the composition is wrong:

- **The feet line and the figure height, as fractions of the canvas,** on every
  new pose. A fixed sprite box across all poses means a pose rendered at a
  different scale does not error, it makes the character grow mid-move.
- **The subject's scale when it leaves the ground.** The generator drew the
  character about a fifth smaller in every airborne pose, consistently, on both
  services. Measure the head — the one landmark a dive does not stretch — not
  the feet line or the silhouette height, neither of which exists on a body in
  flight.
- **Where the composition's ruler actually sits inside the plate,** in image
  pixels, and write the raw numbers into the CSS comment as divisions rather
  than as decimal copies, so the chain can be re-derived. A background plate is
  the ruler; a new plate invalidates every number hung off it.
- **A run, not a span.** A measuring script that took the outermost bright
  pixels in a row put a crossbar 350px too high, because a row crossing two
  floodlights spans the frame while being two small blobs. Measure a contiguous
  run.
- **Verify a shared coordinate space rather than assuming one.** "4k at 2:3" is
  not exactly 2:3, and a service that rounded it differently would need every
  pose padded before keying.

## `raw/` is gitignored

Sources and unoptimised exports go in `raw/`; `tools/optimize.py` writes
`assets/img/` and **those** are committed. A sibling repo in this family shipped
22 MB of source renders to a public GitHub repo, and they stayed downloadable
from raw.githubusercontent.com long after the Pages site had been cleaned.

What is kept instead is the recipe — the model, the prompts, the job ids and the
framing every render had to hit — because the art is reproducible from it and
the blobs never need to be. Put the recipe in the campaign's own `docs/`, which
the deploy allowlist does not copy.

## `tools/optimize.py`

```
python -m pip install "pillow>=10" pillow-avif-plugin
python tools/optimize.py                            # every file in raw/img/
python tools/optimize.py hero.png                   # just one
python tools/optimize.py hero.png --widths 375,1280,1920
python tools/optimize.py logo.png --keep-alpha      # do not flatten
```

Run by hand, never at deploy time. For each source it writes
`assets/img/<name>-<width>.avif` and `.webp`; a source with no `--widths` is
written once at its own size with no width suffix. AVIF quality 50, WebP 80.

Transparency is flattened onto `--navy-950` unless `--keep-alpha` is passed: an
alpha channel costs more than the edge it buys on art sitting on a solid stage,
and flattening onto the page's own backdrop is what stops a grey or white halo
at the edge.

In the markup, put the AVIF `<source>` first and the **widest** media query
first. First match wins, and reversing it downloads the 375px crop to every
desktop.

**Never ship the Figma PNG.** One 1.7 MB export became a 23 KB AVIF in the
landing this is taken from, and looks the same. Figma will also not render a
node above its natural size, so a mobile artboard exports at 1x only — for a
retina cut, export the node at 2x from Figma and feed that in.

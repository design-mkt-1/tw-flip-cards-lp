"""Render the three sounds this landing makes.

The cards had none: turning one, marking it off, and the win were all silent,
which on a page whose whole mechanic is a flip reads as a page that has not
loaded. The clips are written here rather than sourced, for the same reason
tw-penalty writes its confetti and its keeper's head-drop -- the output is
reproducible from this repository, carries no third-party licence onto a
commercial landing page, and can be re-tuned by editing a number instead of
finding another clip that nearly fits.

    python tools/sfx.py

Deterministic: every random draw comes from a seeded generator, so a rerun
writes byte-identical files and a diff means somebody changed the recipe.

Requires numpy and lameenc for the MP3 write -- `pip install numpy lameenc`.
Neither is needed to run the site.

The three, and what they are made of:

    flip  a short paper swish plus the tap of a card landing. Band-limited
          around 2kHz, because a card is not a snare and the top end is what
          makes a flick sound like a click.
    pip   the progress mark filling. One tone, 60ms, an octave above the
          card's tap -- it plays three times a visit and has to be a tick,
          not a note.
    win   a rising third into a soft shimmer. It plays under the card's own
          reveal animation and 240ms before the dialog, so it has to be over
          by the time the form appears.
"""
import numpy as np
import lameenc

SR = 44100
BITRATE = 128
OUT = "campaign/assets/audio/"

# ── helpers ──────────────────────────────────────────────────────

def seconds(t):
    return int(SR * t)


def shape(x, lo=None, hi=None, order=4):
    """Filter in the frequency domain.

    One-pole magnitudes applied to the spectrum, which needs no filter state
    and no scipy. lo is a high-pass corner, hi a low-pass corner, both in Hz.

    order is what makes it usable on noise. A single pole rolls off 6dB an
    octave, and against a flat spectrum that is barely a filter at all: the
    first cut of this file asked for a 7kHz low-pass on the confetti and got
    a burst whose energy still centred on 9.8kHz, which is hiss rather than
    paper. Four cascaded poles is 24dB an octave and actually removes what it
    was pointed at. Measure the centroid after changing this, not the corner.
    """
    spec = np.fft.rfft(x)
    freq = np.fft.rfftfreq(len(x), 1.0 / SR)
    gain = np.ones_like(freq)
    if lo:
        gain *= (freq / np.sqrt(freq ** 2 + lo ** 2)) ** order
    if hi:
        gain *= (hi / np.sqrt(freq ** 2 + hi ** 2)) ** order
    return np.fft.irfft(spec * gain, n=len(x))


def decay(n, tau, attack=0.002):
    """Fast attack, exponential fall. tau is the time to 1/e, in seconds."""
    t = np.arange(n) / SR
    rise = np.clip(t / max(attack, 1e-6), 0, 1)
    return rise * np.exp(-t / tau)


def normalise(x, peak):
    top = np.max(np.abs(x))
    return x * (peak / top) if top > 0 else x


def fade_out(x, t=0.02):
    """A buffer that stops mid-swing clicks. Always end on silence."""
    n = min(seconds(t), len(x))
    x[-n:] *= np.linspace(1, 0, n)
    return x


def write(name, x):
    x = fade_out(normalise(x, 0.89))
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")

    enc = lameenc.Encoder()
    enc.set_bit_rate(BITRATE)
    enc.set_in_sample_rate(SR)
    enc.set_channels(1)
    enc.set_quality(2)
    mp3 = enc.encode(pcm.tobytes()) + enc.flush()

    path = OUT + name + ".mp3"
    with open(path, "wb") as f:
        f.write(mp3)
    print("%-14s %5.2fs  %6d bytes" % (path, len(x) / SR, len(mp3)))



# ── the card turning ─────────────────────────────────────────────

def flip(rng):
    """Paper moving, then the corner landing.

    Two parts, and the order is the whole sound: the swish is the card in the
    air and the tap is it arriving, 90ms later, which is roughly where the
    CSS rotation lands (--cmp-flip-ms is 520ms, and the face is past the
    edge-on point by then).
    """
    n = seconds(0.42)

    # The swish. Noise with the low end taken out -- paper has no body -- and
    # a band around 2kHz, which is where a card's own rustle sits.
    swish = shape(_noise(n, rng), lo=900, hi=4200)
    swish = normalise(swish, 1.0) * decay(n, 0.075, attack=0.012)

    # The tap. A short filtered burst 90ms in, plus enough low end to be felt
    # rather than only heard on a phone speaker.
    tap = np.zeros(n)
    m = seconds(0.16)
    start = seconds(0.09)
    click = shape(_noise(m, rng), lo=300, hi=2600)
    click = normalise(click, 1.0) * decay(m, 0.028, attack=0.001)
    body = np.sin(2 * np.pi * 180 * np.arange(m) / SR) * decay(m, 0.035, attack=0.002)
    tap[start:start + m] = click * 0.8 + body * 0.35

    return swish * 0.55 + tap


# ── the progress mark ────────────────────────────────────────────

def pip(rng):
    """One tick. It plays three times a visit, so it stays out of the way.

    A single tone with a fast decay and a hint of noise on the attack: the
    noise is what stops it reading as a musical note, which at three
    repetitions would start to sound like a phrase going somewhere.
    """
    n = seconds(0.14)
    t = np.arange(n) / SR

    tone = np.sin(2 * np.pi * 880 * t) * decay(n, 0.045, attack=0.001)
    edge = normalise(shape(_noise(n, rng), lo=1800, hi=7000), 1.0)
    edge *= decay(n, 0.012, attack=0.0008)

    return tone * 0.85 + edge * 0.22


# ── the win ──────────────────────────────────────────────────────

def win(rng):
    """A rising major third, then a shimmer under it.

    Under a second, because it starts when the board goes to its reveal phase
    and the registration dialog opens 240ms later: a longer sound would still
    be playing over the form, which is somebody else's moment.

    The two notes are 587 and 880 -- D5 and A5, a fifth rather than a third,
    because the third sat close enough to the pip's own 880 to read as the
    same sound arriving twice.
    """
    n = seconds(0.9)
    t = np.arange(n) / SR

    def note(freq, at, tau, level):
        out = np.zeros(n)
        start = seconds(at)
        m = n - start
        tt = np.arange(m) / SR
        # A second partial an octave up, quiet: one sine alone is a test tone.
        wave = np.sin(2 * np.pi * freq * tt) + 0.28 * np.sin(2 * np.pi * freq * 2 * tt)
        out[start:] = wave * decay(m, tau, attack=0.006)
        return out * level

    body = note(587, 0.0, 0.30, 0.55) + note(880, 0.11, 0.42, 0.60)

    # The shimmer: high noise that arrives with the second note and falls away
    # slowly, so the sound ends on air rather than on a cut tone.
    shimmer = normalise(shape(_noise(n, rng), lo=4000), 1.0)
    shimmer *= decay(n, 0.34, attack=0.10)

    return body + shimmer * 0.16


def _noise(n, rng):
    return rng.standard_normal(n)


# ── ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    write("flip", flip(np.random.default_rng(20260905)))
    write("pip", pip(np.random.default_rng(7)))
    write("win", win(np.random.default_rng(31)))

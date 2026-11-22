"""Does anything on the deck collide with anything else?

python-pptx gives boxes, not ink. A box can be twice as tall as the words inside it, so this wraps
every paragraph with the metrics the renderer uses (Liberation Sans, metric-compatible with Arial),
builds the ink rectangle, and then tests four things per slide:

  1. ink leaves the canvas, or runs into the committee's logo strip at the bottom
  2. two blocks of text overlap on the page
  3. text sits on top of a capture or a chart
  4. text sits on top of a hairline

It also reports ink that spills out of the box that was given to it, which is where overlap comes
from in the first place.

Run:  .venv/bin/python tools/check_deck_layout.py [deck.pptx]
Exit: 0 when clean, 1 with a list of collisions.
"""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import ImageFont
from pptx import Presentation
from pptx.enum.text import PP_ALIGN

ROOT = Path(__file__).resolve().parents[1]
DECK = ROOT / "demo" / "deck" / "Pasok_DemoDay_2026.pptx"
REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
EMU = 914400
SLACK = 0.02          # inches; below this two edges are touching, not colliding
LOGO_TOP = 6.30       # text below this line reaches the committee's logo strip
CANVAS = (13.333, 7.5)


class Ink:
    __slots__ = ("x0", "y0", "x1", "y1", "label")

    def __init__(self, x0, y0, x1, y1, label):
        self.x0, self.y0, self.x1, self.y1, self.label = x0, y0, x1, y1, label

    def overlaps(self, other) -> tuple[float, float]:
        ox = min(self.x1, other.x1) - max(self.x0, other.x0)
        oy = min(self.y1, other.y1) - max(self.y0, other.y0)
        return ox, oy


def _font(bold: bool, px: float) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(BOLD if bold else REG, max(1, int(round(px))))


def _lines(text: str, font, max_w_px: float) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    out, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if font.getlength(trial) <= max_w_px or not cur:
            cur = trial
        else:
            out.append(cur)
            cur = w
    out.append(cur)
    return out


def text_ink(shape) -> Ink | None:
    tf = shape.text_frame
    raw = tf.text.strip()
    if not raw:
        return None
    w_in = shape.width / EMU - (tf.margin_left + tf.margin_right) / EMU
    max_w_px = max(1.0, w_in * 96)
    height = 0.0
    widest = 0.0
    for p in tf.paragraphs:
        runs = [r for r in p.runs if r.text]
        size = max((r.font.size.pt if r.font.size else 12) for r in runs) if runs else 12
        bold = any(bool(r.font.bold) for r in runs)
        px = size / 72 * 96
        font = _font(bold, px)
        lines = _lines(p.text, font, max_w_px)
        widest = max(widest, max(font.getlength(ln) for ln in lines) / 96)
        spacing = p.line_spacing if isinstance(p.line_spacing, float) else 1.0
        height += len(lines) * (size / 72) * 1.2 * spacing
        if p.space_after is not None:
            height += p.space_after.pt / 72
    left = shape.left / EMU + tf.margin_left / EMU
    top = shape.top / EMU + tf.margin_top / EMU
    right = left + w_in
    if tf.paragraphs and tf.paragraphs[0].alignment == PP_ALIGN.RIGHT:
        left = right - widest
    else:
        right = left + widest
    label = raw.replace("\n", " ")[:52]
    return Ink(left, top, right, top + height, label)


def main() -> int:
    deck = Path(sys.argv[1]) if len(sys.argv) > 1 else DECK
    prs = Presentation(deck)
    fails: list[str] = []
    spill: list[str] = []

    for n, slide in enumerate(prs.slides, 1):
        texts: list[Ink] = []
        pictures: list[Ink] = []
        lines: list[Ink] = []
        for sh in slide.shapes:
            box = Ink(sh.left / EMU, sh.top / EMU, (sh.left + sh.width) / EMU,
                      (sh.top + sh.height) / EMU, sh.shape_type)
            if sh.shape_type == 13 or sh.__class__.__name__ == "Picture":      # picture
                full_bleed = (box.x1 - box.x0) > 13.2 and (box.y1 - box.y0) > 7.4
                if not full_bleed:                                              # the template art is not a collision
                    pictures.append(box)
                continue
            if sh.has_text_frame:
                ink = text_ink(sh)
                if ink is None:
                    continue
                texts.append(ink)
                if ink.y1 - ink.y0 > box.y1 - box.y0 + 0.03:
                    spill.append(f"slide {n}: {ink.label!r} needs {ink.y1 - ink.y0:.2f} in "
                                 f"but its box is {box.y1 - box.y0:.2f} in")
            elif box.y1 - box.y0 <= 0.06 and box.x1 - box.x0 > 0.5:             # hairline
                lines.append(box)

        for t in texts:
            if t.x1 > CANVAS[0] - 0.08 or t.y1 > CANVAS[1] - 0.06:
                fails.append(f"slide {n}: {t.label!r} leaves the canvas at "
                             f"({t.x1:.2f}, {t.y1:.2f})")
            page_number = (t.x1 - t.x0) < 0.7 and (t.y1 - t.y0) < 0.3 and t.x0 > 4.0
            if t.y1 > LOGO_TOP and not page_number:
                fails.append(f"slide {n}: {t.label!r} runs into the logo strip at y={t.y1:.2f}")
            for p in pictures:
                ox, oy = t.overlaps(p)
                if ox > SLACK and oy > SLACK:
                    fails.append(f"slide {n}: {t.label!r} sits on a picture "
                                 f"({ox:.2f} x {oy:.2f} in)")
            for ln in lines:
                ox, oy = t.overlaps(ln)
                if ox > SLACK and oy > SLACK:
                    fails.append(f"slide {n}: {t.label!r} sits on a hairline "
                                 f"({ox:.2f} x {oy:.2f} in)")

        for pic in pictures:
            if pic.y1 > LOGO_TOP:
                fails.append(f"slide {n}: a picture reaches y={pic.y1:.2f}, into the logo strip")

        for i in range(len(texts)):
            for j in range(i + 1, len(texts)):
                a, b = texts[i], texts[j]
                ox, oy = a.overlaps(b)
                if ox > SLACK and oy > SLACK:
                    fails.append(f"slide {n}: {a.label!r} overlaps {b.label!r} "
                                 f"({ox:.2f} x {oy:.2f} in)")

    print(f"{deck.name}: {len(prs.slides)} slides")
    for s in spill:
        print(f"  tight  {s}")
    if fails:
        for f in fails:
            print(f"  FAIL   {f}")
        print(f"\n{len(fails)} collisions, {len(spill)} boxes too short")
        return 1
    print(f"  ok     nothing overlaps, nothing leaves the page "
          f"({len(spill)} boxes are tighter than their ink)")
    return 0


if __name__ == "__main__":
    sys.exit(main())

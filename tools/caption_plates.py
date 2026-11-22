"""Caption plates for the demo video: a scrim, a rule, a kicker and one line.

The band that used to sit under the picture read as a sticker: a hard paper rectangle
pasted over the bottom of the frame. This draws a transparent full-frame plate instead, so
ffmpeg can fade it in and out over the recording.
"""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1920, 1080
INK = (255, 255, 255)
KICK = (200, 184, 255)
RULE = (108, 75, 224)
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_BOOK = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"


def _scrim() -> Image.Image:
    plate = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    px = plate.load()
    top = H - 260
    for y in range(top, H):
        a = int(200 * ((y - top) / 260) ** 0.85)
        for x in range(W):
            px[x, y] = (8, 8, 12, a)
    return plate


def plate(kicker: str, line: str, out: Path) -> Path:
    img = _scrim()
    d = ImageDraw.Draw(img)
    d.rectangle([72, 938, 78, 1002], fill=RULE + (255,))
    kfont = ImageFont.truetype(FONT_BOLD, 24)
    lfont = ImageFont.truetype(FONT_BOLD, 40)
    d.text((104, 936), kicker.upper(), font=kfont, fill=KICK)
    d.text((104, 970), line, font=lfont, fill=INK)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out)
    return out

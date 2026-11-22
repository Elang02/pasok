#!/usr/bin/env python3
"""Build the Demo Day video from the deck and the running console.

The video has three kinds of footage, and all three are produced here rather
than recorded by hand:

    slides   rendered from demo/deck/Pasok_DemoDay_2026.pdf
    console  the web console answering a question, recorded with Playwright
    orders   the order desk page, same recorder

Every segment is normalised to 1920x1080 at 30 fps and carries one caption,
so a number that changes later changes in one manifest and not in a video
editor. Rebuilding is `python tools/make_demo_video.py` with the console
running on port 8090.

Usage:
    .venv/bin/python tools/make_demo_video.py            # build everything
    .venv/bin/python tools/make_demo_video.py --keep     # keep temp clips
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECK_PDF = ROOT / "demo" / "deck" / "Pasok_DemoDay_2026.pdf"
OUT_DIR = ROOT / "demo" / "video"
OUT_MP4 = OUT_DIR / "Pasok_DemoDay_2026.mp4"
COVER = OUT_DIR / "cover.png"
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
CONSOLE_URL = "http://127.0.0.1:8090/"
ORDERS_URL = "http://127.0.0.1:8090/orders"

# One entry per shot: (kind, payload, seconds, caption).
# kind "slide" -> payload is the 1-based page of the PDF.
# kind "clip"  -> payload is a recorded file already on disk.
SHOTS: list[tuple[str, object, float, str]] = [
    ("slide", 1, 5.0, "Pasok decides what to reorder, week after week"),
    ("slide", 2, 6.0, "600 SKUs, one buyer, and a calendar that moves under them"),
    ("slide", 3, 6.0, "Orders amplify demand: 2.68x unguarded, 0.24x with the guardrail"),
    ("clip", "console", 24.0, "The console answers a buyer's question from the same artefacts"),
    ("slide", 5, 6.0, "Ask it in words: the console answers from the same artefacts"),
    ("slide", 6, 7.0, "Which products a holiday moves: a normal day beside the peak"),
    ("slide", 7, 6.0, "One order, every line explained from the trace"),
    ("slide", 9, 6.0, "Supplier reliability is measured, not assumed"),
    ("slide", 10, 6.0, "Three guardrails run on every order; the replay proves them"),
    ("slide", 13, 7.0, "One snapshot: what went out, what waited, what came back"),
    ("clip", "orders", 10.0, "The order desk, one row per run"),
    ("slide", 14, 6.0, "What it does, beside numbers published outside"),
    ("slide", 15, 6.0, "Team Pasok, BINUS Alam Sutera, 31 October 2026"),
]


def run(cmd: list[str]) -> None:
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"command failed: {' '.join(cmd[:4])}\n{r.stderr[-2000:]}")


def slides(tmp: Path) -> dict[int, Path]:
    """Render the PDF pages to PNG at the video's pixel size."""
    run(["pdftoppm", "-r", "150", "-png", str(DECK_PDF), str(tmp / "slide")])
    out = {}
    for p in sorted(tmp.glob("slide-*.png")):
        num = int(p.stem.split("-")[-1])
        out[num] = p
    if not out:
        raise SystemExit("no slides rendered")
    return out


def record(tmp: Path) -> dict[str, Path]:
    """Capture the console and the order desk as frame sequences.

    Playwright's own video writer needs a bundled ffmpeg that has no build for
    this distribution, so the recorder takes stills instead: one screenshot per
    step of the interaction, assembled at a fixed frame rate. The result shows
    the question being typed and the answer arriving, which is what the video
    needs, and it uses the ffmpeg already on the box.
    """
    from playwright.sync_api import sync_playwright

    FPS = 5
    clips: dict[str, Path] = {}

    def frames(page, out: Path, seconds: float, step_ms: int = 1000 / FPS) -> int:
        n = 0
        target = int(seconds * FPS)
        while n < target:
            page.screenshot(path=str(out / f"f-{n:05d}.png"))
            page.wait_for_timeout(step_ms)
            n += 1
        return n

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        for name, url in (("console", CONSOLE_URL), ("orders", ORDERS_URL)):
            vdir = tmp / f"frames-{name}"
            vdir.mkdir(parents=True, exist_ok=True)
            page = browser.new_page(viewport={"width": 1920, "height": 1080})
            page.goto(url, wait_until="domcontentloaded")
            page.wait_for_timeout(1200)
            if name == "console":
                box = page.locator("#q, textarea, input[type=text]").first
                box.click()
                question = "What needs more stock for a spike next month?"
                # Typed slowly so the still sequence carries the keystrokes.
                box.type(question, delay=18)
                page.wait_for_timeout(400)
                page.keyboard.press("Enter")
                n = frames(page, vdir, 20.0)
            else:
                n = 0
                for _ in range(10):
                    page.mouse.wheel(0, 120)
                    n += frames(page, vdir, 0.8, 200)
            clip = vdir / "clip.mp4"
            run([
                "ffmpeg", "-y", "-v", "error", "-framerate", str(FPS),
                "-i", str(vdir / "f-%05d.png"), "-c:v", "libx264",
                "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
                str(clip),
            ])
            clips[name] = clip
            page.close()
        browser.close()
    return clips


def wrap(text: str, width: int = 58) -> list[str]:
    """Split a caption into at most two lines of roughly equal length."""
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    if len(lines) > 2:  # keep the tail rather than dropping it silently
        lines = [lines[0], " ".join(lines[1:])]
    return lines


BAND = 80          # height of the paper strip under the frame
FRAME_H = 1080 - BAND
PAPER = (247, 243, 234)
INK = (42, 38, 34)
CAPTION_FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
CAPTION_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"


def caption_strip(text: str, out: Path) -> None:
    """Render the caption as a PNG strip the width of the frame."""
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1920, BAND), PAPER)
    draw = ImageDraw.Draw(img)
    lines = wrap(text, 78)
    size = 30 if len(lines) == 1 else 24
    font = ImageFont.truetype(CAPTION_BOLD if len(lines) == 1 else CAPTION_FONT, size)
    total = sum(draw.textbbox((0, 0), line, font=font)[3] for line in lines) + 6 * (len(lines) - 1)
    y = (BAND - total) / 2 - 2
    for line in lines:
        left, top, right, bottom = draw.textbbox((0, 0), line, font=font)
        draw.text(((1920 - (right - left)) / 2 - left, y - top), line, font=font, fill=INK)
        y += (bottom - top) + 6
    img.save(out)


def normalise(src: Path, dst: Path, seconds: float, strip: Path, tmp: Path) -> None:
    """Fit the picture above the paper band, overlay the caption, hold the last frame."""
    vf = (
        f"scale=1920:{FRAME_H}:force_original_aspect_ratio=decrease,"
        f"pad=1920:{FRAME_H}:(ow-iw)/2:(oh-ih)/2:color=0xF7F3EA,"
        f"pad=1920:1080:0:0:color=0xF7F3EA,setsar=1,fps=30"
    )
    if src.suffix.lower() != ".png":
        vf += f",tpad=stop_mode=clone:stop_duration={seconds}"
    vf += f"[base];[base][1:v]overlay=0:{FRAME_H}:format=auto"
    lead = ["-loop", "1"] if src.suffix.lower() == ".png" else []
    run([
        "ffmpeg", "-y", "-v", "error", *lead,
        "-i", str(src), "-loop", "1", "-i", str(strip), "-t", f"{seconds}",
        "-filter_complex", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-pix_fmt", "yuv420p", "-an", str(dst),
    ])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="keep the temp clips")
    a = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="pasok-video-"))
    try:
        pages = slides(tmp)
        clips = record(tmp)
        pieces: list[Path] = []
        strips: dict[int, Path] = {}
        for i, (kind, payload, secs, cap) in enumerate(SHOTS):
            strip = tmp / f"cap-{i:02d}.png"
            caption_strip(cap, strip)
            strips[i] = strip
            src = pages[int(payload)] if kind == "slide" else clips[str(payload)]
            dst = tmp / f"part-{i:02d}.mp4"
            normalise(src, dst, secs, strip, tmp)
            pieces.append(dst)
            print(f"shot {i:02d}  {secs:4.1f}s  {cap}")

        lst = tmp / "concat.txt"
        lst.write_text("".join(f"file '{p}'\n" for p in pieces))
        run([
            "ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
            "-i", str(lst), "-c", "copy", str(OUT_MP4),
        ])
        run([
            "ffmpeg", "-y", "-v", "error", "-i", str(OUT_MP4),
            "-vf", "select=eq(n\\,0)", "-vframes", "1", str(COVER),
        ])
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration,size",
             "-of", "default=nw=1", str(OUT_MP4)],
            capture_output=True, text=True,
        ).stdout.strip()
        print(f"\n{OUT_MP4.relative_to(ROOT)}\n{probe}")
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
        else:
            print(f"clips kept in {tmp}")
    except SystemExit:
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

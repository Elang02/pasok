"""Record the product, not the deck: five screens, five captions.

Each chapter opens the running console at 127.0.0.1:8090, performs one action (type a
question, scroll the order log), and is normalised to 1920x1080 with the same paper
caption band the demo video uses. Output: demo/video/Pasok_features.mp4.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

from make_demo_video import BAND, FRAME_H, caption_strip, normalise, run

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "demo" / "video"
BASE = "http://127.0.0.1:8090"

# (name, path, action, seconds, caption)
CHAPTERS = [
    ("week", "/", "ask_week", 20.0,
     "Open the desk and ask what to order this week"),
    ("why", "/", "ask_why", 22.0,
     "Ask why an order exists and it reads the arithmetic back"),
    ("event", "/", "ask_event", 22.0,
     "Ask which products an event moves, and it names them"),
    ("orders", "/orders", "scroll", 14.0,
     "Every run is logged: what went out, what waited"),
    ("transfer", "/", "ask_transfer", 18.0,
     "Surplus here, short there: it moves stock before buying more"),
]

QUESTIONS = {
    "ask_week": "What should we order this week?",
    "ask_why": "Why did we order 3,375 units of SKU0041?",
    "ask_event": "What is the nearest event, and what product that spike",
    "ask_transfer": "What should we transfer between warehouses?",
}


FPS = 10


def record(name: str, path: str, action: str, seconds: float, tmp: Path) -> Path:
    """Open the page, do one thing, and keep a frame every 1/FPS second."""
    shots = tmp / name
    shots.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        page = browser.new_page(viewport={"width": 1600, "height": 900})
        page.goto(BASE + path, wait_until="networkidle")
        page.wait_for_timeout(700)
        n = 0

        def grab() -> None:
            nonlocal n
            page.screenshot(path=str(shots / f"f{n:05d}.png"))
            n += 1

        if action in QUESTIONS:
            box = page.locator("input[type=text], textarea").first
            box.click()
            box.fill(QUESTIONS[action])
            for _ in range(6):
                grab()
            box.press("Enter")
            try:
                page.wait_for_selector("div.answer", timeout=25000)
                page.locator("div.answer").last.scroll_into_view_if_needed()
                page.wait_for_timeout(600)
            except Exception:
                pass
            started = time.monotonic()
            while time.monotonic() - started < seconds:
                grab()
                time.sleep(1 / FPS)
        else:
            started = time.monotonic()
            for _ in range(4):
                page.mouse.wheel(0, 520)
                for _ in range(10):
                    grab()
                    time.sleep(1 / FPS)
            while time.monotonic() - started < seconds:
                grab()
                time.sleep(1 / FPS)
        browser.close()
    listing = tmp / f"{name}.txt"
    listing.write_text("".join(f"file '{f}'\nduration 1\n" for f in sorted(shots.glob("*.png"))))
    out = tmp / f"{name}.mp4"
    run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
         "-vf", f"fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "veryfast",
         "-crf", "20", str(out)])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="feat_"))
    clips = []
    try:
        for i, (name, path, action, seconds, caption) in enumerate(CHAPTERS, 1):
            raw = record(name, path, action, seconds, tmp)
            strip = tmp / f"cap{i}.png"
            caption_strip(caption, strip)
            out = tmp / f"clip{i}.mp4"
            normalise(raw, out, seconds, strip, tmp)
            clips.append(out)
            print(f"chapter {i}: {name} {seconds:.0f}s")
        listing = tmp / "list.txt"
        listing.write_text("".join(f"file '{c}'\n" for c in clips))
        final = OUT_DIR / "Pasok_features.mp4"
        run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0",
             "-i", str(listing), "-c", "copy", str(final)])
        import subprocess as _sp
        probe = _sp.check_output(["ffprobe", "-v", "error", "-show_entries",
                                  "format=duration,size", "-of", "csv=p=0", str(final)]).decode()
        print(final)
        print(probe.strip())
    finally:
        if not a.keep:
            shutil.rmtree(tmp, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Record the console as one continuous screen recording under Xvfb.

Xvfb gives Chrome a display; ffmpeg records that display with x11grab while Playwright works
the page. One take, no cuts, no page reloads between questions — a reload flashes the whole
frame white, which is what made the earlier edit look like it was blinking.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "video" / "Pasok_features.mp4"
DURS = Path("/tmp/narasi_dur.json")
DISPLAY = ":99"
W, H = 1920, 1080
BASE = os.environ.get("PASOK_CONSOLE", "http://127.0.0.1:8090")

QUESTIONS = [
    "What should we order this week?",
    "Why did we order 2,079 units of SKU0456?",
    "What is the nearest event, and what product that spike",
    "What runs out this week?",
    "What should we transfer between warehouses?",
]


def start_xvfb() -> subprocess.Popen:
    subprocess.run(["pkill", "-f", f"Xvfb {DISPLAY}"], check=False)
    time.sleep(0.6)
    proc = subprocess.Popen(["Xvfb", DISPLAY, "-screen", "0", f"{W}x{H}x24", "-nolisten", "tcp"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(1.2)
    return proc


def start_recorder(path: Path) -> subprocess.Popen:
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "x11grab", "-draw_mouse", "0",
           "-video_size", f"{W}x{H}", "-framerate", "30", "-i", DISPLAY,
           "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-pix_fmt", "yuv420p", str(path)]
    return subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def wait_settled(page) -> None:
    page.wait_for_selector("div.answer", timeout=40000)
    last, quiet = -1, 0.0
    while quiet < 1.6:
        n = page.evaluate("()=>{const a=[...document.querySelectorAll('div.answer')];return a.length?a[a.length-1].innerText.length:0}")
        quiet = quiet + 0.2 if n == last else 0.0
        last = n
        page.wait_for_timeout(200)


def main() -> int:
    xvfb = start_xvfb()
    raw = Path("/tmp/pasok_screen.mp4")

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False,
                                    args=["--window-position=0,0", f"--window-size={W},{H}",
                                          "--kiosk", "--no-first-run", "--hide-scrollbars"],
                                    env={**os.environ, "DISPLAY": DISPLAY})
        page = browser.new_page(viewport={"width": W, "height": H})
        page.goto(BASE + "/", wait_until="networkidle")
        page.wait_for_timeout(2500)
        _rec0 = time.time()
        rec = start_recorder(raw)
        time.sleep(1.0)
        box = page.locator("input[type=text], textarea").first
        marks = []
        for i, question in enumerate(QUESTIONS):
            _t0 = time.time()
            box.click()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            page.wait_for_timeout(250)
            box.type(question, delay=45)
            page.wait_for_timeout(300)
            box.press("Enter")
            wait_settled(page)
            page.evaluate("""() => {
                const all = [...document.querySelectorAll('div.answer')];
                const a = all[all.length - 1];
                if (!a) return;
                const r = a.getBoundingClientRect();
                window.scrollBy(0, r.top - 150);
            }""")
            _want = 6.0
            try:
                _d = json.loads(DURS.read_text()).get(str(i + 1), 0)
                _want = max(3.0, _d - (time.time() - _t0) + 5.0)
            except Exception:
                pass
            page.wait_for_timeout(int(_want * 1000))
            marks.append({'chapter': i + 1, 'start': round(_t0 - _rec0, 2),
                          'end': round(time.time() - _rec0, 2)})
        Path('/tmp/pasok_marks.json').write_text(json.dumps({'marks': marks}, indent=2))
        page.wait_for_timeout(600)
        browser.close()

    rec.send_signal(signal.SIGINT)
    rec.wait(timeout=90)
    xvfb.send_signal(signal.SIGTERM)

    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(raw),
                    "-vf", "scale=1920:1080:flags=lanczos",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)], check=True)
    dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(OUT)]).decode().strip()
    print(json.dumps({"out": str(OUT), "bytes": OUT.stat().st_size, "seconds": dur}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

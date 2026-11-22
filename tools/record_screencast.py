"""Record the console with Chrome's own screencast, not a screen grabber.

`Page.startScreencast` makes the browser capture its own page and hand back JPEG frames the
moment the page changes, each with the timestamp it was taken. The video is assembled from
those timestamps, so the motion is the page's motion, captured live — nothing is stitched
from stills shot by a separate tool.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "video" / "Pasok_features.mp4"
FRAMES = Path("/tmp/screencast")
W, H = 1600, 900
BASE = os.environ.get("PASOK_CONSOLE", "http://127.0.0.1:8090")

QUESTIONS = [
    ("this week", "What should we order this week?"),
    ("why", "Why did we order 3,375 units of SKU0041?"),
    ("event", "What is the nearest event, and what product that spike"),
    ("runs out", "What runs out this week?"),
    ("transfer", "What should we transfer between warehouses?"),
]


def wait_settled(page) -> None:
    page.wait_for_selector("div.answer", timeout=40000)
    last, quiet = -1, 0.0
    while quiet < 1.6:
        n = page.evaluate("()=>{const a=[...document.querySelectorAll('div.answer')];return a.length?a[a.length-1].innerText.length:0}")
        quiet = quiet + 0.2 if n == last else 0.0
        last = n
        page.wait_for_timeout(200)


def main() -> int:
    FRAMES.mkdir(parents=True, exist_ok=True)
    for old in FRAMES.glob("*.jpg"):
        old.unlink()
    order: list[tuple[str, float]] = []
    t0 = time.monotonic()

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=False,
                                    args=["--window-position=0,0", f"--window-size={W},{H}",
                                          "--kiosk", "--no-first-run", "--hide-scrollbars"],
                                    env={**os.environ, "DISPLAY": ":99"})
        page = browser.new_page(viewport={"width": W, "height": H})
        cdp = page.context.new_cdp_session(page)
        cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 85,
                                          "maxWidth": W, "maxHeight": H, "everyNthFrame": 1})

        def on_frame(params):
            name = f"{len(order):05d}.jpg"
            (FRAMES / name).write_bytes(__import__("base64").b64decode(params["data"]))
            order.append((name, params["metadata"]["timestamp"]))
            cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})

        cdp.on("Page.screencastFrame", on_frame)

        for key, question in QUESTIONS:
            page.goto(BASE + "/", wait_until="networkidle")
            page.wait_for_timeout(900)
            box = page.locator("input[type=text], textarea").first
            box.click()
            page.wait_for_timeout(300)
            box.type(question, delay=45)
            page.wait_for_timeout(350)
            box.press("Enter")
            wait_settled(page)
            page.mouse.wheel(0, 700)
            page.wait_for_timeout(2200)
        page.wait_for_timeout(400)
        cdp.send("Page.stopScreencast")
        browser.close()

    if len(order) < 30:
        print("not enough frames", len(order))
        return 1
    base_ts = order[0][1]
    lines = ["ffconcat version 1.0"]
    for i, (name, ts) in enumerate(order):
        nxt = order[i + 1][1] if i + 1 < len(order) else ts + 0.05
        dur = max(0.008, min(0.5, nxt - ts))
        lines += [f"file '{FRAMES / name}'", f"duration {dur:.4f}"]
    lines += [f"file '{FRAMES / order[-1][0]}'"]
    listing = Path("/tmp/screencast.ffconcat")
    listing.write_text("\n".join(lines) + "\n")

    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing),
                    "-vf", "fps=30,scale=1920:-2,pad=1920:1080:0:(oh-ih)/2:color=#0F0F13",
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)], check=True)
    print(json.dumps({"frames": len(order), "seconds": round(order[-1][1] - base_ts, 1),
                      "bytes": OUT.stat().st_size}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

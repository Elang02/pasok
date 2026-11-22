"""Cut the recorded take into the demo video and lay the caption plates over it.

Input: /tmp/pasok_screen.mp4 (x11grab) and /tmp/pasok_marks.json (chapter times).
Output: demo/video/Pasok_features.mp4, 1920x1080, chapters captioned with a scrim, a rule,
a kicker and one line, each fading in and out rather than appearing as a pasted band.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from caption_plates import plate  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "demo" / "video" / "Pasok_features.mp4"
RAW = Path("/tmp/pasok_screen.mp4")
MARKS = Path("/tmp/pasok_marks.json")
FADE_IN, FADE_OUT = 0.45, 0.55


def main() -> int:
    marks = json.loads(MARKS.read_text())["marks"]
    total = json.loads(MARKS.read_text())["duration"]
    tmp = Path("/tmp/plates")
    tmp.mkdir(exist_ok=True)

    inputs = ["-i", str(RAW)]
    filters = ["[0:v]crop=1600:800:0:96,scale=1920:960:flags=lanczos,"
               "pad=1920:1080:0:0:color=#0F0F13[base]"]
    last = "base"
    for i, m in enumerate(marks, start=1):
        dur = max(0.8, m["end"] - m["start"])
        png = plate(f"{i:02d} / {m['key']}", m["caption"], tmp / f"plate{i}.png")
        inputs += ["-loop", "1", "-t", f"{dur:.2f}", "-i", str(png)]
        filters.append(
            f"[{i}:v]format=rgba,fade=t=in:st=0:d={FADE_IN}:alpha=1,"
            f"fade=t=out:st={max(0.0, dur - FADE_OUT):.2f}:d={FADE_OUT}:alpha=1,"
            f"setpts=PTS-STARTPTS+{m['start']:.2f}/TB[cap{i}]")
        nxt = f"v{i}"
        filters.append(f"[{last}][cap{i}]overlay=0:0:enable='between(t,{m['start']:.2f},{m['end']:.2f})'[{nxt}]")
        last = nxt
    filters.append(f"[{last}]trim=0:{total:.2f},format=yuv420p[vout]")

    cmd = ["ffmpeg", "-y", "-v", "error", *inputs, "-filter_complex", ";".join(filters),
           "-map", "[vout]", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
           "-movflags", "+faststart", str(OUT)]
    subprocess.run(cmd, check=True)
    size = OUT.stat().st_size
    dur = subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                   "-of", "csv=p=0", str(OUT)]).decode().strip()
    print(f"{OUT} {size} {dur}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

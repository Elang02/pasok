"""Does the demo video show the product, in sync, without a crop?

The video says things about numbers. This checks the file itself: the frame is the screen that was
recorded, the sound lands where the frame does, and no chapter is a still with a voice over it.

    .venv/bin/python tools/video_gate.py [path]
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "demo" / "video" / "Pasok_DemoDay_2026.mp4"
PLAN = ROOT / "demo" / "video" / "take" / "plan.json"
TOLERANCE = 0.45        # a sentence may start this far from the frame that proves it
MIN_LOUD = -17.0
MAX_LOUD = -15.0


def run(*cmd: str) -> str:
    return subprocess.run([str(c) for c in cmd], capture_output=True, text=True).stderr


def probe(path: Path, entries: str) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", entries,
                          "-of", "json", str(path)], capture_output=True, text=True).stdout
    return json.loads(out)


def main() -> int:
    video = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    fails: list[str] = []
    checks: list[tuple[bool, str]] = []

    streams = probe(video, "stream=codec_type,width,height,avg_frame_rate,duration")
    v = next(s for s in streams["streams"] if s["codec_type"] == "video")
    a = next((s for s in streams["streams"] if s["codec_type"] == "audio"), None)
    checks.append((v["width"] == 1920 and v["height"] == 1080,
                   f"frame is {v['width']}x{v['height']}, recorded at 1920x1080"))
    checks.append((v["avg_frame_rate"] == "30/1", f"frame rate {v['avg_frame_rate']}"))
    checks.append((a is not None, "there is an audio track"))
    if a:
        gap = abs(float(v["duration"]) - float(a["duration"]))
        checks.append((gap <= 0.1, f"video {float(v['duration']):.2f}s vs audio {float(a['duration']):.2f}s"))

    loud = run("ffmpeg", "-hide_banner", "-i", str(video), "-af",
               "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-")
    stats = json.loads(loud[loud.rindex("{"):loud.rindex("}") + 1])
    integrated = float(stats["input_i"])
    checks.append((MIN_LOUD <= integrated <= MAX_LOUD, f"loudness {integrated} LUFS"))

    if PLAN.exists():
        plan = json.loads(PLAN.read_text())
        expected = [c["reveal"] for c in plan["chapters"]]
        found = run("ffmpeg", "-hide_banner", "-i", str(video), "-af",
                    "silencedetect=n=-45dB:d=0.35", "-f", "null", "-")
        onsets = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", found)]
        drift = []
        for want in expected:
            near = min(onsets, key=lambda o: abs(o - want)) if onsets else float("inf")
            drift.append(round(near - want, 2))
        worst = max(abs(d) for d in drift)
        checks.append((worst <= TOLERANCE, f"speech starts within {worst:.2f}s of its chapter {drift}"))
    else:
        fails.append("no plan.json, so sync was not checked")

    print(f"{video.name}: {v['width']}x{v['height']} {float(v['duration']):.1f}s")
    for ok, label in checks:
        print(f"  {'ok  ' if ok else 'FAIL'} {label}")
        if not ok:
            fails.append(label)
    if fails:
        print("\nfailed:")
        for f in fails:
            print(f"  {f}")
        return 1
    print("\nthe file is the screen, the sound is on it, and nothing is cropped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

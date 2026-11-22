#!/usr/bin/env bash
# Refuse to start a long run on a nearly full disk.
#
# A full disk does not fail loudly: pandas writes a short file, the replay keeps going for a
# while, and the run dies hours later with a half-written folder. This guard checks free space
# first and prunes replay folders that are not in KEEP, then re-checks.
#
#   tools/disk_guard.sh [needed_mb]
set -euo pipefail

need_mb="${1:-2000}"
root=/home/ubuntu/pasok
keep="replay2026_v28 replay2026_v29 replay2026_m"

free_mb() { df -Pm / | awk 'NR==2 {print $4}'; }

avail=$(free_mb)
if [ "$avail" -ge "$need_mb" ]; then
  echo "disk ok: ${avail}MB free"
  exit 0
fi

echo "disk low: ${avail}MB free, need ${need_mb}MB — pruning old replays" >&2
for d in "$root"/data/sim/replay2026_*; do
  [ -d "$d" ] || continue
  name=$(basename "$d")
  case " $keep " in *" $name "*) continue ;; esac
  echo "  removing $name ($(du -sh "$d" | cut -f1))" >&2
  rm -rf "$d"
done

avail=$(free_mb)
if [ "$avail" -lt "$need_mb" ]; then
  echo "still only ${avail}MB free after pruning — stop here and free space by hand" >&2
  exit 1
fi
echo "disk ok after pruning: ${avail}MB free"

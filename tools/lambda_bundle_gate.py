"""Gate: the data snapshot inside the Lambda bundle must match the repo artefacts.

Rationale: the public endpoint answers from the CSV snapshot in its zip. A code fix that changes
an artefact is invisible there until the bundle is refreshed and redeployed, so this gate fails
on drift instead of letting the deployed system disagree with the console.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
r = subprocess.run([str(ROOT / ".venv" / "bin" / "python"),
                    str(ROOT / "tools" / "refresh_lambda_bundle.py"), "--check"],
                   capture_output=True, text=True, cwd=ROOT)
out = (r.stdout + r.stderr).strip()
if r.returncode == 0:
    print(f"lambda bundle matches the repo artefacts ({out.splitlines()[0]})")
    sys.exit(0)
print("lambda bundle DRIFT vs repo artefacts")
print(out)
sys.exit(1)

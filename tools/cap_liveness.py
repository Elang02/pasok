"""Apakah plafon varians benar-benar menyala? Cetak jumlahnya, jangan dirasakan.

Plafon menyala tepat ketika `raw_order > cap_units`. Dipanggil tanpa argumen ia memakai snapshot
hidup dan knob yang berlaku. Dipanggil dengan `--expect-fire` ia mengetatkan knob sampai plafon
harus memotong, supaya terbukti aturannya tersambung dan bukan sekadar tertulis.

Keluar dengan status 1 kalau harapannya tidak terpenuhi.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parents[1]
PY = str(ROOT / ".venv" / "bin" / "python")
AGENT = str(ROOT / "src" / "agents" / "decision.py")


def run(env_extra: dict[str, str]) -> "pd.DataFrame":  # noqa: F821
    import pandas as pd

    out = pathlib.Path(tempfile.mkdtemp(prefix="caplive_"))
    env = dict(os.environ)
    env["PASOK_AGENT_OUT"] = str(out)
    env.update(env_extra)
    subprocess.run([PY, AGENT], cwd=ROOT, env=env, check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return pd.read_csv(out / "decisions.csv")


def main() -> int:
    import pandas as pd

    expect_fire = "--expect-fire" in sys.argv
    default = run({})
    tighten = run({"PASOK_CAP_HEADROOM": "1.02"}) if expect_fire else None

    def report(nama: str, d: "pd.DataFrame") -> int:
        fires = int((d.raw_order > d.cap_units + 0.5).sum())
        cut = float((d.raw_order - d.cap_units).clip(lower=0).sum())
        fill_min = float(d.fill_rate_used.min())
        print(f"{nama}: memesan {int((d.guarded_order > 0).sum())} SKU | plafon menyala {fires} SKU "
              f"| terpotong {cut:,.0f} unit | fill terendah {fill_min:.3f}")
        return fires

    fires_default = report("knob yang berlaku", default)

    if not expect_fire:
        print("Plafon hidup kalau angkanya di atas nol. Ubah kebijakannya, jangan gate-nya."
              if fires_default == 0 else "Plafon memotong pesanan pada snapshot ini.")
        return 0

    fires_tight = report("knob diketatkan (1.02)", tighten)
    if fires_tight == 0:
        print("GAGAL: plafon tidak menyala walau knob diketatkan, aturannya tidak tersambung.")
        return 1
    print(f"TERBUKTI: plafon tersambung ({fires_tight} SKU dipotong saat knob diketatkan), "
          f"dan tidak menyala pada kebijakan yang berlaku ({fires_default} SKU) karena fill "
          f"terendah {float(default.fill_rate_used.min()):.3f} masih di atas 1/1.25.")
    return 0


if __name__ == "__main__":
    sys.exit(main())


#!/usr/bin/env python
"""Siapkan tangkapan layar demo lewat Chrome DevTools Protocol.

Menjalankan: .venv/bin/python tools/demo_shots.py
Menaruh PNG di shots/demo-*.png dan meringkas isi DOM tiap halaman, sehingga isi
tangkapan bisa diperiksa tanpa membuka gambarnya.
"""
from __future__ import annotations

import base64
import json
import pathlib
import time
import urllib.request

import websocket

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / "shots"
OUT.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8090"
CDP = "http://127.0.0.1:9222"


def new_tab(url: str) -> dict:
    req = urllib.request.Request(f"{CDP}/json/new?{url}", method="PUT")
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def close_tab(tid: str) -> None:
    try:
        urllib.request.urlopen(f"{CDP}/json/close/{tid}", timeout=10).read()
    except Exception:
        pass


class Tab:
    def __init__(self, url: str):
        self.info = new_tab(url)
        self.id = self.info["id"]
        self.ws = websocket.create_connection(self.info["webSocketDebuggerUrl"], timeout=60)
        self.n = 0

    def send(self, method: str, **params):
        self.n += 1
        self.ws.send(json.dumps({"id": self.n, "method": method, "params": params}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.n:
                if "error" in msg:
                    raise RuntimeError(msg["error"])
                return msg.get("result", {})

    def js(self, expr: str):
        r = self.send("Runtime.evaluate", expression=expr, awaitPromise=True, returnByValue=True)
        return r.get("result", {}).get("value")

    def shot(self, name: str) -> tuple:
        m = self.send("Page.getLayoutMetrics")
        w = int(m["cssContentSize"]["width"])
        h = int(m["cssContentSize"]["height"])
        self.send("Emulation.setDeviceMetricsOverride", width=max(w, 1440),
                  height=min(h, 6000), deviceScaleFactor=1, mobile=False)
        time.sleep(0.6)
        r = self.send("Page.captureScreenshot", format="png", captureBeyondViewport=True)
        p = OUT / f"demo-{name}.png"
        p.write_bytes(base64.b64decode(r["data"]))
        return p, p.stat().st_size, w, h

    def close(self):
        try:
            self.ws.close()
        except Exception:
            pass
        close_tab(self.id)


PAGES = [
    ("01-console", "/", "document.querySelectorAll('.t').length"),
    ("02-orders", "/orders", "document.querySelectorAll('#runs tr').length"),
    ("03-receiving", "/receiving", "document.querySelectorAll('#bysupplier tr').length"),
    ("04-stock", "/health", "document.querySelectorAll('#classes tr').length"),
    ("05-transfers", "/transfers", "document.querySelectorAll('#ledger tr').length"),
    ("06-suppliers", "/suppliers", "document.querySelectorAll('#perf tr').length"),
    ("07-cities", "/geography", "document.querySelectorAll('#cities tr').length"),
    ("08-loop", "/loop", "document.querySelectorAll('.checks li').length"),
    ("09-panel", "/panel", "document.body.innerText.length"),
]

ASK = "which SKUs run out this week, and is anything waiting for me?"


def main() -> int:
    for name, path, check in PAGES:
        t = Tab(BASE + path)
        try:
            time.sleep(4)                      # biar skrip halaman selesai mengambil data
            n = t.js(check)
            p, size, w, h = t.shot(name)
            print(f"{name:14s} {w}x{h}  {size:>8,} bytes  isi: {check.split('(')[0][-22:]} = {n}")
        finally:
            t.close()

    # halaman konsol: ajukan pertanyaan, tunggu jejak berpikir, buka, lalu potret
    t = Tab(BASE + "/")
    try:
        time.sleep(3)
        t.js(f"""(() => {{
            const q = document.querySelector('#q');
            q.value = {ASK!r};
            q.dispatchEvent(new Event('input', {{bubbles: true}}));
            const b = document.querySelector('#send') || document.querySelector('button');
            b.click();
            return 'sent';
        }})()""")
        for _ in range(40):
            time.sleep(1)
            if t.js("!!document.querySelector('.think')"):
                break
        t.js("(() => { const d = document.querySelector('.think'); if (d) d.open = true; return true; })()")
        time.sleep(1)
        dom = t.js("""(() => {
            const t = document.querySelector('.think');
            const a = document.querySelector('.answer');
            return JSON.stringify({
              thought: t ? t.querySelector('summary').innerText : '',
              steps: t ? [...t.querySelectorAll('li')].map(li => li.innerText.replace(/\\n/g, ' | ')) : [],
              answer: a ? a.innerText.slice(0, 260) : '',
            });
        })()""")
        print("\nkonsol menjawab:")
        for line in json.loads(dom).items():
            print("  ", line)
        p, size, w, h = t.shot("10-chat-reasoning")
        print(f"\n  tangkapan: {p.name} {w}x{h} {size:,} bytes")
    finally:
        t.close()
    print("\nsemua tangkapan ada di", OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

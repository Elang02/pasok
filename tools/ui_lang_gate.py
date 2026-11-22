#!/usr/bin/env python3
"""
Gate the text a reader actually sees on the Pasok console.
==========================================================

The console is judged in English on 31 October, so this gate enforces English. It
replaces `ui_text_gate.py`, which enforced the opposite: it banned English jargon from
an Indonesian console. The stripping work is the same, and it is the part worth keeping,
because telling apart the text that reaches the screen from the text that only reaches
the reader of the source is the hard half.

The old gate failed the whole site once because it read `wape` out of a dict key and
`snapshot` out of a placeholder comment. Note that `snapshot` is now a legitimate English
word on screen ("Snapshot 11 October 2026"), so it is deliberately not on any list here.

What it reports:

  1. Indonesian words left on screen
  2. machine codes printed at a reader (ESCALATED, HOLD_ONE_CYCLE, WAPE)
  3. an em dash or a semicolon in visible text
  4. a number grouped the Indonesian way, 1.234, where English reads 1,234

What it strips:

  .html  comments, style bodies and script bodies from the node text, then the human
         words inside <script> string literals are taken back, because a console builds
         its labels in JS and injects them as innerHTML and a gate that drops the script
         body is blind to exactly the words the operator sees.
  .py    comments, docstrings, HTML placeholder tokens, .get("key") lookups, dict keys,
         quoted subscripts, .append("token"), annotations inside a def signature, method
         and class names, machine keyword arguments, the intent key tables, and any
         remaining attribute access.

Usage:
    python3 tools/ui_lang_gate.py [path ...]     # default: web/

Exit 0 when clean, 1 when anything is still on screen.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

# Indonesian left on screen. Matched on word boundaries, so `dan` does not fire inside
# `Demand` and `stok` does not fire inside `stock`.
INDONESIAN = {
    # function words
    "dan": "and", "atau": "or", "yang": "that/which", "untuk": "for", "dari": "from",
    "dengan": "with", "tidak": "not", "belum": "not yet", "sudah": "already",
    "adalah": "is", "ini": "this", "itu": "that", "pada": "at/on", "akan": "will",
    "karena": "because", "jadi": "so", "juga": "also", "masih": "still", "bisa": "can",
    "harus": "must", "tanpa": "without", "semua": "all", "tiap": "each",
    "setiap": "every", "kalau": "if", "jika": "if", "saat": "when", "lalu": "then",
    "lebih": "more", "paling": "most", "agar": "so that", "biar": "so that",
    "hanya": "only", "saja": "only", "punya": "has", "memakai": "uses", "pakai": "use",
    "tapi": "but", "namun": "however", "kenapa": "why", "apa": "what",
    "berapa": "how many", "mana": "which", "siapa": "who", "kapan": "when",
    # actions a reader is told to take
    "baca": "read", "lihat": "see", "tekan": "press", "pilih": "pick", "tulis": "type",
    "jalankan": "run", "hitung": "count", "urut": "sort", "tampil": "shown",
    "coba": "try", "ulang": "repeat", "tanya": "ask", "ketik": "type",
    # the domain
    "rekaman": "snapshot", "stok": "stock", "barang": "category", "agen": "agent",
    "otomatis": "auto-issued", "manusia": "human", "antrian": "queue",
    "persetujuan": "approval", "keandalan": "reliability", "permintaan": "demand",
    "posisi": "position", "keputusan": "decision", "pengirim": "executor",
    "penerima": "intake", "notifikasi": "notification", "belajar": "learn",
    "kenaikan": "uplift", "lonjakan": "spike", "habis": "runs out", "minggu": "week",
    "bulan": "month", "depan": "next", "sisa": "remaining", "hari": "day",
    "keluar": "out", "tahan": "hold", "siklus": "cycle", "pembatas": "guardrail",
    "ramalan": "forecast", "salah": "wrong", "nilai": "value", "serah": "hand-off",
    "bukti": "evidence", "angka": "figure", "berkas": "file", "artefak": "artefact",
    "jumlah": "count", "baris": "row", "kolom": "column", "lulus": "passed",
    "gagal": "failed", "terpenuhi": "fill rate", "kirim": "send",
    "kedaluwarsa": "expiry", "pengecualian": "exception", "pesanan": "order",
    "jaringan": "network", "performa": "performance", "mandiri": "autonomous",
    "peta": "map", "jejak": "trace", "konsol": "console",
    "kirimkan": "send", "tampilkan": "show", "masukkan": "enter", "selesai": "done",
    "berjalan": "running", "menunggu": "waiting", "menyimpan": "saving",
}

# machine codes and internal terms that must never be printed at a reader
MACHINE = {
    "ESCALATED": "awaiting approval",
    "AUTO_ISSUED": "auto-issued",
    "HOLD_ONE_CYCLE": "held one cycle",
    "HELD_FOR_APPROVAL": "awaiting approval",
    "SUPPLY_SHORT": "supply short",
    "SUPPLY_AND_LEAD": "supply and lead time short",
    "ON_PLAN": "on plan",
    "WAPE": "forecast error",
    "OTIF": "on time in full",
    "rampa": "event uplift",
    "amplifikasi": "amplification",
}

# A number grouped the Indonesian way. Only the unambiguous shapes count: two or more
# groups (1.234.567), or a group followed by a decimal comma (1.234,56). A single group
# is genuinely ambiguous, because `458.861` and `0.959` are the same shape and only one
# of them is a mistake, so the gate stays quiet on it rather than crying wolf.
ID_NUMBER = re.compile(r"\b\d{1,3}(?:\.\d{3}){2,}\b|\b\d{1,3}(?:\.\d{3})+,\d+\b")

# an HTML entity ends in a semicolon and is not punctuation the reader sees
ENTITY = re.compile(r"&[a-zA-Z#0-9]+;")

# A prose semicolon is followed on the same line by a space and a word. A statement
# terminator in code is followed by a newline, a brace or nothing. That difference is
# what tells the two apart without having to parse JavaScript.
SEMI_PROSE = re.compile(r";[ \t]+[A-Za-z]")

# The buyer reads the page, not a developer. `docs/PLAIN_LANGUAGE.md` is the contract.
# These are the words a judge knows from the proposal and a buyer has to translate, so
# they may appear as a figure label but never as the sentence.
JARGON = {
    "guardrail": "say 'order rule'",
    "velocity": "say 'sells per day'",
    "sellable": "say 'available now'",
    "days of cover": "say 'days of stock left'",
    "lead p90": "say 'worst-case delivery time'",
    "lead time": "say 'delivery time'",
    "amplification": "say 'how much orders swing'",
    "event uplift": "say 'times normal during the event'",
    "peak multiplier": "say 'times normal at peak'",
    "exception queue": "say 'waiting for a person'",
    "escalated": "say 'waiting for a person'",
    "auto-issued": "say 'placed without a person'",
    "rationale": "say 'Why'",
    "uplift": "say 'times normal'",
    "on time (": "say 'delivered complete and on time'",
}

# One phrase survives on purpose: the contribution the proposal names. Deleting it would
# delete a named contribution from the page the judges score.
JARGON_ALLOWED = ["order stability guardrails"]

# A CSS declaration, which a console writes inside a JS string. No space before the
# colon and none right after it, which prose almost never does ("Note: this is fine").
# The tail may cross a newline, because a formatted console writes
# `margin-bottom:10px\n;` when a rule is assembled from several strings.
CSS_DECL = re.compile(r"(?<=[\s;{}\"'`])[a-z][a-z-]*:[^\s;{}][^;{}]*;")

# A literal that is nothing but a separator is a data delimiter, never prose:
# reason.split(";"). Same for a matcher token, which is compared with `in` and is
# what the user may type, never what the page shows: `"habis" in low`.
SEPARATOR_LITERAL = re.compile(r"""["'];["']""")

# A stored value that is COMPARED against, or used as a dictionary key, is not text on
# screen. `status == "ESCALATED"` reads the ordering system's own value, and
# `{"escalated": "awaiting approval"}` is a lookup table, so neither can reach the reader as
# a word. Only a code that survives into a sentence is a leak.
STORED_VALUE = re.compile(
    r"(?:==|!=|<=|>=|\.get\(|\.startswith\(|\.endswith\(|\bin\s*\()"
    r"[ \t]*f?[\"\']([^\"\'\n]{2,60})[\"\']")
DICT_KEY = re.compile(r"[\"\']([^\"\'\n]{2,60})[\"\']\s*:")
MATCH_TOKEN = re.compile(r"""["'][^"\n]{1,80}["']\s+in\s+\w+|'[^'\n]{1,80}'\s+in\s+\w+""")


def visible_text(path: Path) -> str:
    """The text a reader sees, with code shapes removed."""
    text = path.read_text()
    if path.suffix == ".html":
        no_tags = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
        # The provenance footer is a technical annotation, not buyer prose: it names the service
        # and the model behind a number, so it keeps exact field words (`escalated`,
        # `auto-issued`) and the model id. `docs/PLAIN_LANGUAGE.md` governs the page, not the
        # footnote that says which service answered.
        no_tags = re.sub(r"<footer[^>]*class=\"[^\"]*prov[^\"]*\"[^>]*>.*?</footer>", " ",
                         no_tags, flags=re.S)
        no_tags = re.sub(r"<style[^>]*>.*?</style>", " ", no_tags, flags=re.S)
        # remove the script BODY from the node text: the literals inside it are handled
        # separately below. Stripping only the <script> tags would leave the whole
        # program standing as "visible text".
        no_tags = re.sub(r"<script[^>]*>.*?</script>", " ", no_tags, flags=re.S)
        nodes = re.sub(r"<[^>]+>", " ", no_tags)
        js_words = []
        for m in re.finditer(r"<script[^>]*>(.*?)</script>", text, flags=re.S):
            for s in re.finditer(r'"([^"\\\n]{2,160})"|\'([^\'\\\n]{2,160})\'|`([^`]{2,600})`',
                                 m.group(1), flags=re.S):
                lit = s.group(0)[1:-1]
                # a JS identifier is not a label: element ids (tk-wape), dict keys and
                # property reads (d.snapshot)
                if re.fullmatch(r"[A-Za-z_$][\w$.\-]*", lit.strip()):
                    continue
                clean = re.sub(r"<[^>]*>", " ", lit)
                clean = re.sub(r"\$\{[^}]*\}", " ", clean)
                clean = re.sub(r"&[a-z]+;", " ", clean)
                clean = re.sub(r"\\[nrt]", " ", clean)
                # A quote pair can start at one string's closing quote and end at the
                # next string's opening quote, which captures the code lying between
                # them. Braces and arrow functions are never in a label, and a CSS
                # declaration is code, so both screen the candidate out.
                if re.search(r"[{}]|=>", lit) or CSS_DECL.search(" " + lit):
                    continue
                if len(clean.strip()) >= 3:
                    js_words.append(clean)
        # the same code-shape strips as the .py branch: the JS literal pass captures
        # code lying between two quote pairs, and that code carries semicolons
        js = "\n".join(js_words)
        js = SEPARATOR_LITERAL.sub(" ", js)
        js = CSS_DECL.sub(" ", js)
        return nodes + "\n" + js
    # .py: comments out, docstrings out, then the never-on-screen shapes out.
    text = re.sub(r"#.*$", " ", text, flags=re.M)
    text = re.sub(r'"""(?:.|\n)*?"""', " ", text)
    text = re.sub(r"'''(?:.|\n)*?'''", " ", text)
    # 0. an HTML placeholder token is a comment in the served page: the server swaps it
    #    for the value, the reader never sees the token.
    text = re.sub(r"<!--[^>\n]*-->", " ", text)
    # 1. .get("key") / .get('key') lookups
    text = re.sub(r"\.get\(\s*['\"][\w.]+['\"]\s*\)", " ", text)
    # 2. a dict/JSON key: a bare identifier in quotes, followed by a colon
    text = re.sub(r"(['\"])([A-Za-z_]\w*)\1\s*:", " ", text)
    # 3a. the literal shapes FIRST, before the annotation rule can chew into them
    text = re.sub(r"\.append\(\s*['\"][\w.]+['\"]\s*\)", " ", text)
    # 3b. a type annotation, but only inside a def signature, where it belongs
    def _strip_annotations(m):
        return re.sub(r"\b\w+\s*:\s*[A-Za-z_][\w.\[\], ]*", " ", m.group(0))
    text = re.sub(r"\bdef\s+\w+\s*\([^)]*\)", _strip_annotations, text)
    # 3c. a method or class name
    text = re.sub(r"\bdef\s+\w+", " ", text)
    text = re.sub(r"\bclass\s+\w+", " ", text)
    # 4. a machine keyword argument
    text = re.sub(
        r"\b(?:id|cmd|sort|limit|stage_id|stage|kind|key|field|model|q)\s*=\s*"
        r"(?:\"[^\"\n]*\"|'[^'\n]*')",
        " ", text)
    # 5. the matcher keyboards: what the user may TYPE, never what the page shows.
    #    INTENT_WORDS is a nested list of tuples, so it closes on a bare "]" on its own
    #    line, not the first "]".
    text = re.sub(r"\bINTENT_WORDS\s*=\s*\[.*?\n\]", " ", text, flags=re.S)
    text = re.sub(r"\b(?:ACT_FAST|FULL_LOOP|ACT_WORDS)\s*=\s*\[.*?\]", " ", text, flags=re.S)
    # 5b. an inline matcher: a quoted token compared with `in`
    text = MATCH_TOKEN.sub(" ", text)
    # 6. a quoted subscript, e.g. r["wape"] or _CURVE[-1]["wape"]: a CSV column or a
    #    dict read, never shown. Index-agnostic.
    text = re.sub(r"\[['\"][\w.]+['\"]\]", " ", text)
    text = re.sub(r"\{['\"][\w.]+['\"]\}", " ", text)
    # 6b. a statement separator and a CSS declaration inside a JS string
    text = SEPARATOR_LITERAL.sub(" ", text)
    text = CSS_DECL.sub(" ", text)
    text = STORED_VALUE.sub(" ", text)
    text = DICT_KEY.sub(" ", text)
    # 7. any other attribute access
    text = re.sub(r"\.\w+", " ", text)
    return text


def hits_in(body: str) -> dict[str, int]:
    found: dict[str, int] = {}
    for word in INDONESIAN:
        n = len(re.findall(rf"\b{re.escape(word)}\b", body, re.I))
        if n:
            found[word] = n
    for word in MACHINE:
        n = len(re.findall(rf"\b{re.escape(word)}\b", body))
        if n:
            found[word] = n
    return found


def jargon_hits(body: str) -> dict:
    """The words a buyer has to translate. `docs/PLAIN_LANGUAGE.md` says why."""
    low = body.lower()
    for ok in JARGON_ALLOWED:
        low = low.replace(ok, " ")
    out = {}
    for w, why in JARGON.items():
        pattern = re.escape(w) if w.endswith("(") else r"\b" + re.escape(w) + r"\b"
        n = len(re.findall(pattern, low, re.I))
        if n:
            out[w] = (n, why)
    return out


def main(argv: list[str]) -> int:
    targets = [Path(a) for a in argv[1:]] or [Path("web")]
    dirty = 0
    for t in targets:
        files = sorted(t.glob("*.html")) + sorted(t.glob("*.py")) if t.is_dir() else [t]
        for path in files:
            body = visible_text(path)
            h = hits_in(body)
            dashes = len(re.findall("\u2014", body))
            semis = len(SEMI_PROSE.findall(ENTITY.sub(" ", body)))
            numbers = ID_NUMBER.findall(body)
            jargon = jargon_hits(body)
            if not h and not dashes and not semis and not numbers and not jargon:
                print(f"{path}: clean")
                continue
            dirty += 1
            print(f"\n=== {path} ===")
            for w, n in sorted(h.items(), key=lambda x: -x[1]):
                print(f"  {w:18s} x{n:<3d} -> {INDONESIAN.get(w) or MACHINE[w]}")
            if dashes:
                print(f"  {'em dash':18s} x{dashes:<3d} -> use comma, colon, or period")
            if semis:
                print(f"  {'semicolon':18s} x{semis:<3d} -> use comma, colon, or period")
            if numbers:
                print(f"  {'ID numbers':18s} x{len(numbers):<3d} -> {numbers[:4]}")
            for w, (n, why) in sorted(jargon.items(), key=lambda x: -x[1][0]):
                print(f"  {w:18s} x{n:<3d} -> {why}")
    if dirty:
        print(f"\n{dirty} file(s) still have on-screen text to fix")
        return 1
    print("\nAll visible text is English.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

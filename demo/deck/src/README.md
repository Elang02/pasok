# Deck source (superseded 2026-10-27)

> **Not the shipped deck.** The deck on stage is built by `../build_deck.py` on the
> committee's template. These pages were an earlier attempt that dropped that template and
> are kept only as a record of the typography work.

The Demo Day deck is drawn as SVG pages and exported to PPTX with
[ppt-master](https://github.com/hugohe3/ppt-master) v6.7.3. The PPTX in the
folder above is the shipped artefact; this folder is how it was made.

## What is here

| File | What it is |
|---|---|
| `build_svg.py` | Writes the thirteen pages. Edit here, not in the SVG files, so the grid, the type scale, and the hairlines stay consistent. |
| `P01_cover.svg` … `P13_close.svg` | The pages themselves, generated. 1280 × 720, one committed world: warm paper, ink, a single rust accent. |
| `design_spec.md` | Page-by-page intent, type roles, and palette. |
| `spec_lock.md` | The execution lock ppt-master checks every page against. |

## Rebuild

```bash
python3 demo/deck/src/build_svg.py                  # rewrite the 13 pages
ppt-master/skills/ppt-master/scripts/svg_quality_checker.py <project> --canonical-authoring --stage final --json
ppt-master/skills/ppt-master/scripts/svg_to_pptx.py <project> -o Pasok_DemoDay_2026.pptx
soffice --headless --convert-to pdf Pasok_DemoDay_2026.pptx --outdir .
.venv/bin/python demo/deck/check_deck_numbers.py    # 20 claims against the artefacts
```

`build_svg.py` uses only the standard library. The ppt-master project lives at
`~/work/ppt-master/projects/pasok_demo_ppt169_20261027/`; this folder mirrors its
`svg_output/` plus the two specification files.

## The world the pages live in

Not a deck: a ledger sheet from a warehouse desk. One paper (#F7F3EA), one ink
(#1F1B16), one rust accent (#B4551F) that appears at most twice on a page, and
hairline rules instead of cards. Headlines are Georgia at 44, set tight; numbers
are Georgia too, right-aligned like a book of accounts; everything that is a
label is Segoe UI at 16. Nothing is boxed, nothing is centred, no page carries an
eyebrow above its heading.

Every page keeps the same skeleton: running rule at the top with the page number,
the claim in two lines, a thin rule under it, the evidence, and one closing
sentence at the foot. The numbers are the ones `demo/figures.md` and
`data/agents/targets.json` carry; `check_deck_numbers.py` fails the build if a
digit drifts.

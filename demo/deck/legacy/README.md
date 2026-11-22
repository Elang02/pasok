# The previous deck pipeline

These three scripts built and checked the 13-slide deck that shipped until 26 October
2026. The deck itself is the same length and makes the same argument, but it was drawn
in python-pptx shape by shape, which is why it is kept only for provenance.

The deck now on disk (`demo/deck/Pasok_DemoDay_2026.pptx`) was authored as SVG in the
ppt-master project at `~/work/ppt-master/projects/pasok_demo_ppt169_20261027/`, passed
the ppt-master quality gate (13 of 13 pages), and was exported to native PowerPoint.
Its numbers are checked by `demo/deck/check_deck_numbers.py`, which reads the PPTX and
compares every claim against the artefacts. That check replaces `check_numbers.py`.

`build_deck.py` still runs and still produces a valid deck, but it is not the file we
present. Do not wire it back into the rehearsal script.

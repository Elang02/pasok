#!/bin/bash
# Pasok — full local pipeline (deterministic, no accounts)
# Order matters: consolidation writes the switch proposals the executor reads;
# one_pass runs last so it traces the freshest artefacts.
set -e
cd "$(dirname "$0")"
PY=.venv/bin/python
# scripts import the `src` package, so the repo root must be importable
export PYTHONPATH="$PWD${PYTHONPATH:+:$PYTHONPATH}"

echo "== 0/10 registry_catalog =="; $PY src/demand/registry_catalog.py
echo "== 0b/10 build_prep ==";      $PY tools/build_prep.py
echo "== 1/10 stock_position ==";  $PY src/agents/stock_position.py
echo "== 1b/10 supplier_reliability =="; $PY src/agents/supplier_reliability.py
echo "== 2/10 decision ==";        $PY src/agents/decision.py
echo "== 3/10 consolidation ==";   $PY src/agents/consolidation.py
echo "== 4/10 order_executor ==";  $PY src/agents/order_executor.py
echo "== 5/10 order_intake ==";    $PY src/agents/order_intake.py --reset
echo "== 6/10 notification ==";    $PY src/agents/notification.py
echo "== 7/10 redirect ==";        $PY src/agents/redirect.py
echo "== 8/10 learn ==";           $PY src/agents/learn.py
echo "== 9/10 one_pass ==";        $PY src/agents/one_pass.py
echo "CHAIN OK"

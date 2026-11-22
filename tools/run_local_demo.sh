#!/usr/bin/env bash
# Pasok local demo launcher
# =========================
# Starts the two services you can actually poke at, then tells you what to open:
#
#   1. distributor_api.py  (port 8099) — the distributor's ordering system, with SQLite
#   2. pasok_agent main.py (port 8081) — the agent runtime (BedrockAgentCoreApp contract)
#
# Both are local and neither needs an AWS gate to run. The agent's brain is Bedrock
# Mantle (same account, same models as the AWS lane) so it can answer in words here.
#
# Usage:  bash tools/run_local_demo.sh          # start
#         bash tools/run_local_demo.sh stop     # stop

set -u
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY=$ROOT/.venv/bin/python
AGENTPY=$ROOT/.venv/bin/python
LOG=/tmp/pasok_demo

mkdir -p "$LOG"

stop() {
  pkill -f "distributor_api.py" 2>/dev/null
  pkill -f "pasok_agent" 2>/dev/null
  sleep 1
  echo "stopped."
}

if [ "${1:-}" = "stop" ]; then stop; exit 0; fi

# --- credentials for the Mantle brain -------------------------------------
unset AWS_ACCESS_KEY_ID AWS_SECRET_ACCESS_KEY AWS_SESSION_TOKEN 2>/dev/null || true
export AWS_PROFILE=${AWS_PROFILE:-pasok}
export AWS_REGION=${AWS_REGION:-us-west-2}
export PASOK_MODEL=${PASOK_MODEL:-mantle}

# ATM: kill leftovers so ports are free
pkill -f "distributor_api.py" 2>/dev/null || true
pkill -f "pasok_agent" 2>/dev/null || true
sleep 1

# 1) distributor ordering system
nohup "$PY" "$ROOT/tools/distributor_api.py" --port 8099 >"$LOG/distributor_api.log" 2>&1 &
# 2) agent runtime
cd "$ROOT/agentcore/app/pasok_agent"
nohup "$AGENTPY" -c "import uvicorn; from main import app; uvicorn.run(app, host='127.0.0.1', port=8081)" \
  >"$LOG/agent.log" 2>&1 &

# wait for readiness (poll, no fixed sleep loop)
for i in $(seq 1 30); do
  ok_api=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8099/health 2>/dev/null)
  ok_agent=$(curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8081/ping 2>/dev/null)
  [ "$ok_api" = "200" ] && [ "$ok_agent" = "200" ] && break
  sleep 1
done

echo "-----------------------------------------------"
echo " distributor ordering system   http://127.0.0.1:8099"
echo "   GET  /health  /principals  /orders  /stats"
echo "   GET  /orders/SO-<year>-000001     (with audit trail)"
echo "   POST /orders                    (place an order)"
echo "   POST /receipts                  (post a goods receipt)"
echo
echo " agent runtime                 http://127.0.0.1:8081"
echo "   GET  /ping"
echo "   POST /invocations   {\"prompt\": \"How many orders were escalated?\"}"
echo
echo " database                      $ROOT/data/distributor_api/pasok_distributor.db"
echo " logs                          $LOG/"
echo " model                         $PASOK_MODEL"
echo "-----------------------------------------------"
echo "stop with: bash tools/run_local_demo.sh stop"

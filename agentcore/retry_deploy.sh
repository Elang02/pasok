#!/bin/bash
# Pasok AgentCore deploy retry — runs until both AWS gates clear, then deploys.
# Gates: (1) Bedrock inference authorized, (2) AgentCore Runtime quota > 0.
set -u
export AWS_PROFILE=pasok
export PATH="$HOME/.local/bin:$PATH"
AWS="$HOME/.local/bin/aws"
REGION="us-west-2"
MODEL="us.anthropic.claude-sonnet-4-5-20250929-v1:0"
ROOT="/home/ubuntu/pasok"
LOG="$ROOT/agentcore/retry_deploy.log"

echo "[$(date -u +%FT%TZ)] retry loop start" >> "$LOG"

for i in $(seq 1 288); do   # 288 * 5min = 24h
  # ---- gate 1: Bedrock inference ----
  OUT=$($AWS bedrock-runtime converse --region "$REGION" --model-id "$MODEL" \
        --messages '[{"role":"user","content":[{"text":"ok"}]}]' \
        --inference-config '{"maxTokens":5}' 2>&1)
  if echo "$OUT" | grep -qi "Operation not allowed\|currently being verified"; then
    GATE1="closed"
  elif echo "$OUT" | grep -q '"output"'; then
    GATE1="open"
  else
    GATE1="unknown"
  fi

  # ---- gate 2: AgentCore quota ----
  Q=$($AWS service-quotas list-service-quotas --region "$REGION" \
        --service-code bedrock-agentcore \
        --query "Quotas[?QuotaName=='Total Agents per Account'].Value" --output text 2>/dev/null)
  Q=${Q:-0}

  echo "[$(date -u +%FT%TZ)] iter=$i gate1=$GATE1 quota=$Q" >> "$LOG"

  if [ "$GATE1" = "open" ] && [ "${Q%.*}" -ge 1 ] 2>/dev/null; then
    echo "[$(date -u +%FT%TZ)] BOTH GATES OPEN — deploying" >> "$LOG"
    cd "$ROOT" || exit 1
    agentcore deploy -y --json >> "$LOG" 2>&1
    RC=$?
    echo "[$(date -u +%FT%TZ)] deploy rc=$RC" >> "$LOG"
    if [ $RC -eq 0 ]; then
      echo "[$(date -u +%FT%TZ)] DEPLOY SUCCESS — exiting loop" >> "$LOG"
      exit 0
    fi
    # deploy ran but failed; wait and retry
  fi

  sleep 300
done
echo "[$(date -u +%FT%TZ)] loop exhausted after 24h" >> "$LOG"
exit 1

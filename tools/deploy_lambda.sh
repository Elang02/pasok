#!/bin/bash
# Deploy the Pasok Lambda: refresh the data snapshot, zip the bundle, push the code, smoke test.
#
# The function answers from the CSV snapshot inside its own zip, so the snapshot refresh is part
# of the deploy, not an afterthought. Credentials are the caller's business: this script uses
# AWS_PROFILE if set and fails with a clear message when the account cannot update the function
# (the hackathon account has lambda APIs denied by an organisation SCP).
#
#   PASOK_LAMBDA_FN=my-function AWS_PROFILE=pasok ./tools/deploy_lambda.sh
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
: "${PASOK_LAMBDA_FN:?set PASOK_LAMBDA_FN to the function name}"
REGION="${AWS_REGION:-us-west-2}"
PROFILE_ARG=(); [ -n "${AWS_PROFILE:-}" ] && PROFILE_ARG=(--profile "$AWS_PROFILE")

echo "== 0/4 refresh the bundled snapshot"
$PY tools/refresh_lambda_bundle.py
$PY tools/lambda_bundle_gate.py

echo "== 1/4 zip"
ZIP=/tmp/pasok_lambda.zip
rm -f "$ZIP"
(cd aws/lambda/pasok_agent && zip -qr "$ZIP" . -x "__pycache__/*" "*.bak")
ls -lh "$ZIP"

echo "== 2/4 update-function-code $PASOK_LAMBDA_FN ($REGION)"
aws "${PROFILE_ARG[@]}" lambda update-function-code --region "$REGION" \
    --function-name "$PASOK_LAMBDA_FN" --zip-file "fileb://$ZIP" \
    --query 'LastModified' --output text

echo "== 3/4 wait for the update"
aws "${PROFILE_ARG[@]}" lambda wait function-updated --region "$REGION" --function-name "$PASOK_LAMBDA_FN"

echo "== 4/4 smoke test the public URL"
URL="${PASOK_LAMBDA_URL:-https://vyfesxclb5gwzqqkg5csbkgxeq0jdnpf.lambda-url.us-west-2.on.aws/}"
code=$(curl -s -o /tmp/pasok_lambda_probe.json -w '%{http_code}' -X POST "$URL" \
    -H 'content-type: application/json' -d '{"action":"network"}')
echo "HTTP $code"; head -c 300 /tmp/pasok_lambda_probe.json; echo
[ "$code" = "200" ] || { echo "the endpoint did not answer 200"; exit 1; }
echo "deployed and answering"

# Phase 5 — AWS lane evidence (05-01)

**Date:** 2026-10-09
**Account:** <account-id> (`Elang01`), region `us-west-2`, profile `pasok`

## Proven working

### 1. Account identity
```
$ aws sts get-caller-identity
{
  "UserId": "<account-id>",
  "Account": "<account-id>",
  "Arn": "arn:aws:iam::<account-id>:root"
}
```
`aws account get-account-information` → `AccountState: ACTIVE`, created 2020-05-14.

### 2. The AgentCore runtime code runs and reaches Bedrock
Local serve of `agentcore/app/pasok_agent/main.py` (Strands + `BedrockAgentCoreApp`):

```
$ curl -s http://127.0.0.1:8081/ping
{"status":"Healthy","time_of_last_update":1791545031}

$ curl -s -X POST http://127.0.0.1:8081/invocations \
    -d '{"prompt": "What should I do about SKU0001 this week? ..."}'
data: {"error": "An error occurred (AccessDeniedException) when calling the
ConverseStream operation: Your account is currently being verified. ..."}
```
The HTTP contract works end to end; the only failure is the Bedrock model call, which
is gated at the ACCOUNT level.

### 3. The six tools return real figures (no LLM needed)
```
get_sku_decision('SKU0001')  ->  ... (decision row)
list_exception_skus(3)       ->  SKU0227 cover 0.0d lost_sales 46227.0, ...
get_network_summary()        ->  n_skus 600, orders_placed 583,
                                 amplification raw 1.21 / guarded 0.35 (-72.8%)
```

### 4. Control plane works (only Bedrock inference is gated)
- S3 list: OK
- CloudFormation: OK (CDKToolkit CREATE_COMPLETE)
- ECR describe-repositories: OK
- bedrock-agentcore-control list-agent-runtimes: OK (`[]`)

## Blockers (both external, both AWS-side)

### B1 — Bedrock inference verification
Every `converse` call, including Amazon Nova (no model agreement required), returns:
```
ValidationException: Operation not allowed
```
And via the runtime:
```
AccessDeniedException: Your account is currently being verified.
Verification normally takes less than 2 hours.
```
`aws bedrock get-foundation-model-availability --model-id us.anthropic.claude-sonnet-4-5-...`
→ `authorizationStatus: NOT_AUTHORIZED`, `agreementAvailability: NOT_AVAILABLE`.

**This is not a code bug, not a credential bug, not a WAF problem.** It clears when AWS
finishes verifying the account (the account was only fully activated on 2026-10-09
after the operator updated the default payment method).

### B2 — AgentCore Runtime quota = 0
```
$ aws cloudformation describe-stack-events ... (CREATE_FAILED)
Resource handler returned message: "Limit exceeded for resource of type
'AWS::BedrockAgentCore::Runtime'. Reason: maxAgents limit exceeded for account
<account-id>." (ServiceLimitExceeded)

$ aws service-quotas list-service-quotas --service-code bedrock-agentcore
Total Agents per Account ...... 0.0     (default 1000.0)
Maximum size for a Docker image 0.0
```
Requesting an increase via API is refused: *"You must provide a quota value greater
than the default quota value of 1000.0"* — i.e. the applied value (0) is below the
default, a new-account restriction. It lifts together with B1.

## Deploy log
- `agentcore deploy` reached: validate → sync deps → build CDK → **synthesize CF (OK)**
  → bootstrap CDKToolkit → deploy. Failed at the runtime resource (B2).
- Root cause of the earlier synth failure was fixed: `codeLocation` in
  `agentcore/agentcore.json` resolves relative to the PROJECT ROOT
  (`/home/ubuntu/pasok/`), not to `agentcore/`; an `app/pasok_agent`
  symlink now points at the source of truth under `agentcore/app/pasok_agent`.
- The partial stack was deleted (`AgentCore-PasokAgentCore-default`,
  ROLLBACK_COMPLETE → deleted) so a later retry starts clean.

## Next action (automatic)
A retry loop re-checks both gates and re-runs `agentcore deploy -y` once inference is
authorized and the AgentCore quota is non-zero. No code change is pending.

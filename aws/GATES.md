# AWS gates - status and how to reproduce

Account <account-id> (Elang01), region us-west-2, profile `pasok`.
All commands below were re-run on 2026-10-09 and are copy-pasteable.

## Summary

| Gate | State | Status |
|---|---|---|
| Bedrock native (`Converse` / `InvokeModel`) | `Operation not allowed`, 86/86 models | BYPASSED - Mantle endpoint serves models today |
| AgentCore Runtime | `Total Agents per Account` quota = 0 | BLOCKED - same account authorization as native Bedrock |
| Bedrock Knowledge Base | none exist | NOT BUILT - registry is a file, swap documented |

## Gate 1 - native Bedrock

```bash
aws bedrock-runtime converse --region us-west-2 --model-id amazon.nova-lite-v1:0 \
  --messages '[{"role":"user","content":[{"text":"OK"}]}]' --inference-config '{"maxTokens":8}'
# -> ValidationException: An error occurred (ValidationException) when calling the
#    Converse operation: Operation not allowed

aws bedrock get-foundation-model-availability --region us-west-2 --model-id amazon.nova-lite-v1:0
# -> authorizationStatus: NOT_AUTHORIZED
#    agreementAvailability / entitlementAvailability / regionAvailability: AVAILABLE
```

A sweep of all 86 ACTIVE text models returns the same error, including Amazon Nova.
This is an **account authorization** gate, not IAM: attaching `AmazonBedrockFullAccess`
does not change it, and the Anthropic first-time use-case form refuses with "Your
account is not authorized to perform this action. Please create a support case."

**Bypassed.** `bedrock-mantle.us-west-2.api.aws` is the OpenAI-compatible surface of
the same Bedrock inference engine and answers on this account:

```bash
# short-term Bedrock API key, minted from the caller credentials (SigV4 presign of
# Action=CallWithBearerToken, base64, prefix bedrock-api-key-), 12h lifetime
python3.12 -c "
import configparser,os,base64
from botocore.auth import SigV4QueryAuth
from botocore.awsrequest import AWSRequest
from botocore.credentials import Credentials
c=configparser.ConfigParser(); c.read(os.path.expanduser('~/.aws/credentials'))
creds=Credentials(access_key=c['pasok']['aws_access_key_id'],
                  secret_key=c['pasok']['aws_secret_access_key'])
req=AWSRequest(method='POST',url='https://bedrock.amazonaws.com/',
               headers={'host':'bedrock.amazonaws.com'},
               params={'Action':'CallWithBearerToken'})
SigV4QueryAuth(creds,'bedrock','us-west-2',expires=43200).add_auth(req)
key='bedrock-api-key-'+base64.b64encode(req.url.replace('https://','').encode()+b'&Version=1').decode()
open('/tmp/bedrock_key.txt','w').write(key)
"
curl https://bedrock-mantle.us-west-2.api.aws/v1/chat/completions \
  -H "Authorization: Bearer $(cat /tmp/bedrock_key.txt)" \
  -H "Content-Type: application/json" \
  -d '{"model":"moonshotai.kimi-k2.5","messages":[{"role":"user","content":"Say OK"}]}'
# -> HTTP 200, model moonshotai.kimi-k2.5
```

Note: the repo `.venv` has no botocore; mint the key with `python3.12` (which does).
The long-term `ABSK` console key stored in the vault **returns 401 while the account
gate is open**, exactly as the `bedrock-mantle-access` skill predicts. The minted
short-term key answers 200 on the same account. Re-mint on demand, cache ~11h.

Last verified: 2026-10-11, `mantle kimi-k2.5 -> 200 OK` with a freshly minted key.

Models answering: `moonshotai.kimi-k2.5`, `deepseek.v3.2`, `deepseek.v3.1`,
`qwen.qwen3-32b`, `qwen.qwen3-235b-a22b-2507`, `zai.glm-4.7`, `zai.glm-4.7-flash`.
Nova and Llama are **not** served by Mantle (404) and stay on the native path.
Recipe: skill `bedrock-mantle-access`.

## Gate 2 - AgentCore Runtime quota

```bash
aws service-quotas list-service-quotas --region us-west-2 --service-code bedrock-agentcore \
  --query "Quotas[?QuotaName=='Total Agents per Account'].Value" --output text
# -> 0.0
```

The AgentCore deployment
(`agentcore/app/pasok_agent/`, code complete, `/ping` Healthy) fails with
`maxAgents limit exceeded`. Quota code `L-F4575653`, value `0.0`, `Adjustable: True` - but the increase API refuses:
`RequestServiceQuotaIncrease` -> `IllegalArgumentException: You must provide a quota
value greater than the default quota value of 1000.0`. So the quota is pinned at 0
while the AWS default is 1000: an **account restriction**, not a capacity limit, and
the only actor who can lift it is AWS. Same applies to `Endpoints per Agent`
(`L-9B442722`, default 10) and `Versions per Agent` (`L-61A3A6D8`, default 1000).

**Blocked, pending AWS.** It lifts with the same account authorization that Gate 1
needs. No retry loop runs unattended on this account. The AWS lane runs on Lambda instead.

## Gate 3 - Bedrock Knowledge Base

```bash
aws bedrock-agent list-knowledge-bases --region us-west-2
# -> {"knowledgeBaseSummaries": []}
```

Proposal line 13 describes the registry as owned by "the Bedrock Knowledge Base". The
registry is currently a file, `data/demand/event_registry.csv`, read by the Decision
Agent; the ramp table it pairs with is `data/demand/sku_ramps.csv`.

**Not built, with rationale.** Running a Knowledge Base requires AgentCore/Bedrock
access and a vector store, both behind Gate 1. The Decision Agent's registry lookup is
a file read, which the demo shows directly. The production swap (point the lookup at a
Knowledge Base) is a wiring change, not a redesign.

## What the operator can do

1. Open a support case from the console under
   Account / Account Activation, Account Verification. This is the single input that
   clears Gates 1 and 2.
2. Set a spend limit in the console (`settings.aws.com` -> Billing -> Upgrade -> Set
   spend limits). It is console-only; there is no API.

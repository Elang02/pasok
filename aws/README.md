# Pasok — AWS lane (Lambda + Bedrock)

The AWS lane of Pasok. **AWS hosts the four-agent runtime; Amazon Bedrock serves the LLM
brain via the Mantle compatible endpoint**, with SAP AI Core as fallback.

## Endpoint

```
https://vyfesxclb5gwzqqkg5csbkgxeq0jdnpf.lambda-url.us-west-2.on.aws/
```

Public HTTPS, no credentials required (Function URL, auth NONE).

## API

| Request | Returns |
|---|---|
| `{"action":"network"}` | decision/order/learn summaries (600 SKUs, 166 orders, 166 auto, 0 escalated, amp 1.33→0.36) |
| `{"action":"exceptions","limit":N}` | the exception queue, sorted by urgency |
| `{"action":"sku","sku":"SKU0361"}` | position + decision + order + learn for one SKU |
| `{"action":"ask","prompt":"..."}` | grounded context + a live Bedrock answer (falls back to SAP AI Core) |

## Why the Mantle endpoint

Native `bedrock-runtime` (`Converse`, `InvokeModel`) returns
`ValidationException: Operation not allowed` for **every** model on this account, including
Amazon Nova. `get-foundation-model-availability` reports `authorizationStatus:
NOT_AUTHORIZED` while agreement/entitlement/region are all `AVAILABLE`. That gate is an
account-authorization step (the Anthropic use-case form refuses with "create a support
case"), not a permissions problem.

`bedrock-mantle.<region>.api.aws` is the compatible-APIs surface of the same Bedrock
inference engine and **works on this account** with a short-term Bedrock API key:

- `moonshotai.kimi-k2.5`, `deepseek.v3.2`, `deepseek.v3.1`, `qwen.qwen3-32b`,
  `qwen.qwen3-235b-a22b-2507`, `zai.glm-4.7`, `zai.glm-4.7-flash` → all answer.
- Amazon Nova and Llama are not served through Mantle (404), so they stay on the
  upgrade path.

## Auth

`bedrock_token.py` mints the short-term bearer key with `botocore` (bundled in the Lambda
runtime), mirroring AWS's `aws_bedrock_token_generator`: SigV4-presign a
`bedrock.amazonaws.com` request with `Action=CallWithBearerToken`, base64 it, prefix
`bedrock-api-key-`. Valid 12 hours, cached 11 hours per container, no stored secret.

A long-term console key exists at `Catalog → API keys` (name
`BedrockAPIKey-…-at-<account-id>`, expires Oct 2027) but Bedrock answers `401 Invalid
bearer token` for it while the account sits in the authorization gate. It should start
working once AWS clears the account; the short-term mint needs no such clearing.

## Deploy

```bash
PASOK_LAMBDA_FN=<function name> AWS_PROFILE=<profile> ./tools/deploy_lambda.sh
```

The script refreshes the CSV snapshot inside the bundle first (the endpoint answers straight out of
it), fails the bundle gate on drift, zips, pushes the code and smoke tests the public URL. One
command, no secrets printed.

**The snapshot drifts silently if this is skipped.** A code fix that changes an artefact, such as
a new column in `decisions.csv` or a new count in `decision_summary.json`, is invisible on the
public endpoint until the bundle is refreshed and redeployed. `tools/lambda_bundle_gate.py` fails
on that drift, and on 18 October it found 17 of 23 bundled artefacts behind the repo.

**The bundle is fresh, the endpoint is not.** `tools/refresh_lambda_bundle.py` ran on 26 October
after the catalogue rebuild (25 artefacts, gate green), so the files above describe the 166-order
run. The deployed function still answers from the snapshot it was last given, which is the 125-order
run of 19 October, until the command above is run with working credentials.

**Credentials are currently a blocker.** The function lives in the account that owns the us-west-2
URL; the only profile on this box (`pasok`, account 321043733040) has its lambda APIs denied by an
organisation SCP, so the one remaining step needs the original account's credentials. Everything
else is ready: bundle refreshed, gate green, command above.

## Environment (set on the function, sourced from the vault — never printed)

`SAP_CLIENTID`, `SAP_CLIENTSECRET`, `SAP_TOKEN_URL`, `SAP_API`, `SAP_ORCH_DEPLOYMENT`
(fallback brain), plus optional `BEDROCK_REGION`, `BEDROCK_MODEL`.

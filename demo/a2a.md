# Pasok behind SAP Joule: the A2A path

The organiser's repo ships the official way to let a business user talk to your agent:
SAP Joule calls it over the **A2A protocol**, through a **BTP Destination**. Pasok now
implements that path on our side.

## What the organiser's tutorial does

From `joule_a2a/project/Python-LangGraph/solution/server.py` in the
`SAP-AWS-ID-Hackathon-2026` repo:

```
GET  /.well-known/agent-card.json   -> Agent Card (name, url, skills)
POST /                              -> A2A message/send (task lifecycle)
GET  /health
```

Joule's side: a capability YAML with an `agent-request` action, a `system_alias` that maps
to a BTP Destination, and a `message` action that reads
`apiResponse.body.artifacts[0].parts[0].text`.

## What Pasok has now

| Piece | File | Status |
|---|---|---|
| A2A server (Agent Card + task lifecycle) | `a2a_server.py` | built, runs locally |
| Answers over the artefacts | `pasok_answers.py` | built |
| Capability, official pattern | `joule/pasok_a2a/pasok_capability/` | built, `joule lint` clean |
| Digital assistant descriptor | `joule/pasok_a2a/da.sapdas.yaml` | built |
| BTP Destination | cockpit step | **not created** |
| Cloud Foundry deploy | `cf push` | **not done** |

### The Agent Card we serve

```
name  : Pasok Replenishment Agent
url   : http://localhost:8085        (becomes the CF route once deployed)
skills: network_summary, sku_decision, exception_queue, order_status
```

### The four skills, answered over real A2A

A genuine `message/send` round trip (`/tmp/a2a_probe.py`), not a direct function call:

| Question | Answer |
|---|---|
| How did the network do overall? | 600 SKUs, 458 orders, 384 auto-issued, 74 held (15 credit, 15 near expiry, 6 switch), amp 1.33x -> 0.36x, RPT 600 predictions |
| Which SKUs are in the exception queue? | the queue table with action, cover, principal, event |
| Why was SKU0286 reordered? | cover 8.2 vs target 17.0, P03 lead p90 7.0d, Payday x1.06, 2,092 units |
| Where did PO-0314 end up? | SO-2026-000314, 2,092 ordered, 2,044 accepted, IDR 15,901,480, landed fill 97.70%, 48 short |

### The capability, in the organiser's exact shape

`capability.sapdas.yaml`: `schema_version: 3.28.0`, `namespace: joule.ext`,
`system_aliases.PASOK_AGENT -> destination PASOK_AGENT_A2A`.

`functions/pasok_replenishment.yaml`:

```yaml
action_groups:
  - actions:
      - type: agent-request
        system_alias: PASOK_AGENT
        agent_type: remote
        result_variable: "apiResponse"
      - type: message
        message:
          type: text
          markdown: true
          content: "<? apiResponse.body.artifacts[0].parts[0].text ?>"
```

`joule lint .` -> **No issue found**.

## What remains, exactly

Two steps, both needing the participant's BTP account rather than code:

1. **Cloud Foundry login.** `cf login -a https://api.cf.ap10.hana.ondemand.com --sso` with
   origin key `auisywroy-platform`. This is an interactive browser passcode on the IAS
   account; the CLI is installed (`cf 8.8.0`) and the target org/space is known
   (`SEAIO_aws-sap-hackathon-si4ykj9d` / `hackathon-aigo`).
2. **BTP Destination** `PASOK_AGENT_A2A` pointing at the app's CF route, type HTTP, proxy
   Internet, authentication NoAuthentication (cockpit step, per the organiser's guide).

Then `joule deploy -c -n "pasok_assistant"` and `joule launch pasok_assistant`.

Both are documented in `BTP_Instructions/README.md` of the organiser repo, which is on this
box at `/tmp/panitia_repo` (re-clone with the repo token if it is gone).

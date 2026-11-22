# Pasok — Architecture (Demo Day)

Four-agent replenishment system for Indonesian FMCG distributors, running as an AWS Lambda
service with Bedrock inference through the Mantle endpoint, with SAP as the business system.
AgentCore Runtime is account-gated on this account (quota `Total Agents per Account` = 0,
increase refused), so the loop does not claim to run there.

```mermaid
flowchart TB
    subgraph Signals["Early demand signals"]
        S1["Outlet sell-through history"]
        S2["Event registry<br/>(Ramadan, Lebaran, Imlek, Nyepi — lunar dates drift;<br/>Christmas and New Year are fixed; payday is monthly)"]
        S3["Receiving records<br/>(PO vs actual arrival)"]
    end

    subgraph Core["AWS Lambda service — four-agent loop"]
        D1["<b>Demand Agent</b><br/>weekly per-SKU forecast + CI<br/>learnt event ramp (build/peak/decay)<br/>novelty detection"]
        D2["<b>Stock Position Agent</b><br/>sellable = on-hand + in-transit + open PO<br/>days of cover · coverage-floor &amp; expiry flags"]
        D3["<b>Supplier Reliability Agent</b><br/>learned lead time p50/p90 · fill rate<br/>drift detection"]
        D4["<b>Decision Agent</b> (orchestrator)<br/>weighs holding cost · service level · supplier risk<br/>credit headroom · shelf life · event ramp<br/>actions: auto-issue / hold / redirect / escalate"]
    end

    subgraph Guard["Order-stability guardrails (the differentiator)"]
        G1["1. Smooth forecast before sizing"]
        G2["2. Dampen vs previous order"]
        G3["3. Per-order variance cap"]
    end

    subgraph SAP["SAP AI Core"]
        R["<b>sap-rpt-1.6</b><br/>tabular scoring:<br/>days-of-cover · stockout · expiry"]
        O["<b>gpt-5.4</b> via orchestration<br/>plain-language rationale<br/>per decision"]
    end

    subgraph HITL["Human in the loop"]
        J["<b>Joule</b><br/>pasok_exception_queue<br/>buyer approves escalated orders"]
    end

    subgraph Out["Outcomes"]
        P["Purchase orders<br/>139 auto-issued · 6 escalated"]
        L["Learn step<br/>forecast vs actuals<br/>feeds next cycle"]
    end

    S1 --> D1
    S2 --> D1
    S3 --> D3
    D1 --> D4
    D2 --> D4
    D3 --> D4
    D4 --> G1 --> G2 --> G3
    D4 -.->|"exception queue"| R
    R -.->|"scores"| D4
    D4 -->|"selected SKUs"| O
    O -->|"rationale"| D4
    G3 --> P
    P --> J
    J -->|"approved"| P
    P --> L
    L -.->|"next cycle context"| D1

    classDef agent fill:#e8f0fe,stroke:#1a73e8,stroke-width:2px
    classDef guard fill:#fef7e0,stroke:#f9ab00,stroke-width:2px
    classDef sap fill:#e6f4ea,stroke:#34a853,stroke-width:2px
    classDef hitl fill:#fce8e6,stroke:#d93025,stroke-width:2px
    class D1,D2,D3,D4 agent
    class G1,G2,G3 guard
    class R,O sap
    class J hitl
```

## Reading the diagram

- **The four agents** run as one Lambda service, in process, with Bedrock inference served
  by the Mantle endpoint because native `Converse` is account-gated. The heavy
  number-crunching (forecast, ramp fit, guardrail math, RPT scoring) runs in the offline
  pipeline and hands the service its per-SKU evidence. AgentCore Runtime and Memory are
  blocked on this account, so neither appears as a running component.
- **The guardrails sit between the Decision Agent and the order** — that is where the
  bullwhip is killed. They are not a post-filter; they shape the quantity before it is
  ever issued.
- **SAP AI Core** scores the exception queue with RPT-1.6 and writes the rationale with
  gpt-5.4 through the orchestration deployment.
- **Joule** is the human moment: the buyer sees the escalated queue and approves.
- **The learn step** closes the loop: actual arrivals vs the forecast feed the next
  cycle's context.

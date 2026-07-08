# 5. Competitive landscape

> Note on sourcing: this is a working mental model of the market based on how
> these products are generally positioned, meant for orientation and interview
> prep. Vendor capabilities change fast — before citing specifics in a real
> interview or PRD, verify against each vendor's current docs/analyst reports
> (Gartner, Forrester). Treat the table as a map, not a spec sheet.

## The players and how they're positioned

| Vendor | Positioning (how they're usually described) | Angle relevant to *us* (playbook authoring) |
|---|---|---|
| **Cresta** | Real-time intelligence built from mining call transcripts; guided workflows + coaching. | Strong at *learning* procedures from conversation data — the "V3 flywheel" in our roadmap. Less about SOP-doc ingestion. |
| **Kore.ai** | Broad conversational-AI platform; strong knowledge ingestion + dialog/workflow builders. | Heavy on ingesting knowledge sources; workflow building still largely a build-time authoring effort. |
| **Genesys (Agent Copilot)** | Knowledge surfacing + next-best-action inside the Genesys Cloud flow engine. | Playbook-like logic lives in "Architect" flows — authored in-platform, the manual step we automate. |
| **NICE (Enlighten Copilot / CXone)** | Enlighten AI: guided workflows + real-time compliance & sentiment. | Compliance-guidance-forward — closest in *spirit* to our compliance angle, at run-time. |
| **Cognigy** | Flow-based conversational automation, surfaced to agents. | Flow graphs are authored manually in Cognigy.AI — again, the design-time cost we target. |
| **Salesforce Agentforce / Google CCAI** | Big-platform agent copilots tied to their ecosystems. | Playbook/config authoring is part of setup; automating it accelerates their onboarding too. |

## The pattern across all of them

Nearly every vendor shares the same four-part shape:

1. **Ingest** the company's knowledge/SOPs.
2. **Structure** it into steps/flows/graphs.
3. **Execute** with real-time guidance + compliance checks.
4. **Learn/refine** from transcripts over time.

Most competitive energy goes into steps **3 and 4** (the flashy real-time
experience and the analytics). Step **2 — turning documents into structured
procedures — is still largely manual** across the board. That's the gap this
product targets, and why "automate design time" is a credible wedge rather than a
me-too feature.

## How to talk about competitors in an interview

Good structure for a "how do you compete with X?" answer:

1. **Acknowledge their strength honestly.** (e.g. "Cresta is excellent at learning
   from transcripts.")
2. **Name the gap you attack.** ("But the initial authoring from policy documents
   is still manual and slow — that's the wedge.")
3. **State your defensible moat.** ("Not the LLM — anyone has that. The
   domain-specific schema, the *verifiable* compliance checks, and the
   review workflow that make it trustworthy in regulated settings.")
4. **Position, don't trash.** Ideally you're a layer that *accelerates* whichever
   assist tool the customer already runs (export into their format), rather than
   ripping it out.

## Two contrasting strategic bets (be ready to argue either)

- **"Sell into vendors" (component):** license the authoring engine to Cresta/
  Genesys/NICE as their onboarding accelerator. Faster distribution, but you're
  dependent on partners.
- **"Own the layer" (horizontal):** a vendor-neutral SOP→playbook product the
  enterprise buys directly and exports anywhere. Bigger prize, harder go-to-market,
  needs strong compliance credibility to be trusted.

An interviewer may push you to pick one and defend it — there's no single right
answer, but you should reason about distribution, moat, and buyer (is it the
contact-centre ops leader, the compliance officer, or the vendor's product team?).

← Back to start: [`../README.md`](../README.md)

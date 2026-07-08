# 1. What is "Agent Assist" (and why does this whole product exist)?

> Read this first. It assumes you know nothing about AI or contact centres.
> By the end you'll be able to explain the problem space in an interview.

## The setting: a contact centre

When you call your bank, an airline, or an insurance company, you reach a
**contact centre**. The person you talk to is a **human agent**. Their job is to
resolve your request — block a card, change a booking, file a claim — quickly and
*correctly*.

Two things make this job hard:

1. **There's a lot to know.** Policies are long, change often, and differ by
   product and region. No human remembers all of it.
2. **Some steps are legally required.** In regulated industries (banking,
   insurance, healthcare, telecom) certain steps *must* happen in a certain
   order — verify who you're talking to, confirm consent, capture a one-time
   passcode — or the company is breaking the law and can be fined.

## What "Agent Assist" (a.k.a. "Agent AI") is

**Agent Assist** is software that sits next to the human agent — usually a panel
on their screen — and helps them in real time while they're on the call or chat.
It typically does things like:

- **Surface knowledge:** "Here's the refund policy for this product."
- **Suggest replies:** drafts a message the agent can send with one click.
- **Guide the workflow:** shows the *next step* the agent should take.
- **Check compliance:** warns if a required step was skipped.
- **Summarise:** writes the call notes automatically afterwards.

The vendors you'll hear named in this space: **Cresta, Kore.ai, Genesys (Agent
Copilot), NICE (Enlighten Copilot), Cognigy, Salesforce Agentforce, Google CCAI.**
They differ in details but share this shape: *ingest the company's knowledge →
help the agent act on it in real time.*

## Where "playbooks" fit in

The **workflow-guidance** part above is powered by **playbooks**. A playbook is
the structured, step-by-step procedure for handling one type of request. (The
next doc, `02-what-are-playbooks.md`, is entirely about these.)

The Agent Assist tool watches the conversation, figures out the customer's
**intent** ("they want to block their card"), pulls up the matching playbook, and
walks the agent through it — while checking that the mandatory steps happen.

## The problem THIS project attacks

Here's the twist that makes this a real product opportunity, not just a feature.

Those playbooks don't write themselves. Today, a company that buys Agent Assist
has to **build every playbook by hand**:

- A consultant or analyst reads the company's SOPs (Standard Operating
  Procedures — the long policy documents).
- They manually translate each procedure into steps inside the vendor's tool.
- A compliance expert reviews it.
- They test it, fix it, repeat.

This is called **design time**, and it is *slow and expensive*. A big enterprise
might have hundreds of procedures. Each one is hours of skilled manual work. This
is the number-one thing that delays a customer getting value from the product —
what the industry calls **time-to-value** or **time-to-deploy**.

**Our product's one-sentence pitch:**
> Automatically turn a company's existing SOP documents into structured,
> compliance-checked playbooks — collapsing weeks of manual design work into
> minutes of review — so new agent-assist use cases go live far faster.

We are **not** building the real-time agent panel. We are building the **factory
that manufactures playbooks** for it. That focus is the whole point.

## The key vocabulary (memorise these)

| Term | Plain meaning |
|---|---|
| **Agent** | The human handling the customer (in "agent assist"). |
| **SOP** | Standard Operating Procedure — the company's written policy document. |
| **Playbook** | A structured, ordered set of steps for handling one request type. |
| **Intent** | What the customer is trying to do ("block card", "dispute charge"). |
| **Design time** | The manual work of building playbooks before anything goes live. |
| **Time-to-value / time-to-deploy** | How long from "we bought it" to "it's helping agents". |
| **Compliance gate** | A step that legally must happen (and often in a specific order). |
| **SME** | Subject-Matter Expert — the human who reviews/approves a playbook. |

→ Next: [`02-what-are-playbooks.md`](02-what-are-playbooks.md)

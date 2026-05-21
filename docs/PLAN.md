# Margeen — 40-chunk plan

40 chunks. One per day, with some slack. Each chunk ships:

- A blog article on wiswes.com/blog/margeen-project (≤10 min read)
- Code or notes pushed to this repo (under `chunks/NN/`)
- A short X + LinkedIn post

The plan below is the spine. Order may flex. Anything that's still
"articulated, not built" is marked **[doc]**; anything where code is the
main deliverable is **[code]**.

---

## Phase 1 — Manifesto & foundation (chunks 1–8)

| # | Title | Type |
|---|---|---|
| 01 | Manifesto: 40 days of building an LLM that hunts margin in public | [doc] |
| 02 | The arithmetic of margin: why "15%" almost never means 15% | [doc] |
| 03 | Why AliExpress over Temu, Shopee, CJ, 1688 — a supplier shootout | [doc] |
| 04 | Gemini Flash setup, first prompt, first product idea | [code] |
| 05 | Shopify dev store walkthrough + the product schema we'll target | [code] |
| 06 | The product spec: what an LLM-found product looks like as JSON | [code] |
| 07 | End-to-end manual run: prompt → search → eval → fake sync | [code] |
| 08 | Phase 1 retro + a public dashboard for the daily log | [doc] |

## Phase 2 — MVP: find, evaluate, sync (chunks 9–20)

| # | Title | Type |
|---|---|---|
| 09 | AliExpress data access — Open Platform vs DSers vs scraper backup | [code] |
| 10 | The product search loop: prompt → candidates → re-rank | [code] |
| 11 | Margin calculator v1: COGS, shipping, payment fees, refunds, ad-cost | [code] |
| 12 | The product scorer prompt — and what Gemini Flash gets wrong | [code] |
| 13 | User approval: a 100-line CLI before any UI | [code] |
| 14 | Shopify Admin API: create a real (test) product from agent output | [code] |
| 15 | Images: source from AliExpress, auto-generate alt text, push to Shopify | [code] |
| 16 | Description writing: prompt + edit gate, no raw model output ships | [code] |
| 17 | End-to-end pipeline: prompt → approval → live SKU on Shopify | [code] |
| 18 | First real listing, first real shopper view: what the analytics said | [doc] |
| 19 | Orchestration: doing this without n8n — and a free n8n / Activepieces alt | [code] |
| 20 | Phase 2 retro: cost per chunk, what broke, what to kill | [doc] |

## Phase 3 — Demand-aware, polished, honest (chunks 21–32)

| # | Title | Type |
|---|---|---|
| 21 | Inventory tracking & reorder triggers (still drop-ship, but smarter) | [code] |
| 22 | Local stockpile, articulated: when it makes sense, what it costs | [doc] |
| 23 | Support agent: returns, shipping questions, refunds | [code] |
| 24 | Batching: "10 niches by Friday" — multi-prompt mode | [code] |
| 25 | Programmatic supplier compare: AliExpress vs Temu vs CJ on the same SKU | [code] |
| 26 | Affiliate / referral integrations and why most aren't worth it | [doc] |
| 27 | SEO for an LLM-listed product page (without becoming spam) | [doc] |
| 28 | Paid ads economics: $ in / $ out per SKU, when to stop | [code] |
| 29 | Killing duds: auto-archiving low-converting SKUs after N days | [code] |
| 30 | Margin tiers: A/B/C buckets and what each tier earns the agent | [code] |
| 31 | Drop-ship disclosures, returns policy, the legal minimums | [doc] |
| 32 | Phase 3 retro: what the data is saying about the bet | [doc] |

## Phase 4 — Growth, community, and the post-mortem (chunks 33–40)

| # | Title | Type |
|---|---|---|
| 33 | What N real sales actually look like, item by item | [doc] |
| 34 | The failures post: every bug, every mis-prompt, every wasted dollar | [doc] |
| 35 | "Would I run this for real?" — the honest spreadsheet | [doc] |
| 36 | Open-sourcing the playbook: prompts, schemas, replicable scripts | [code] |
| 37 | Onboarding doc so a stranger can reproduce Margeen in a weekend | [doc] |
| 38 | First external PR + community-shaped backlog | [code] |
| 39 | Hand-off / archive plan: what stays running, what gets frozen | [doc] |
| 40 | Post-mortem and the next bet | [doc] |

---

## DoD per chunk

A chunk is done when **all four** are true:

- [ ] A long-form article (≤10 min read) is published on
      `wiswes.com/blog/margeen-project/<slug>`.
- [ ] Code or notes are pushed to this repo under `chunks/NN/`.
- [ ] An X post draft and a LinkedIn post draft exist for the chunk
      (posted by hand).
- [ ] The "Daily log" table in `README.md` is updated with the new row.

## Kill criteria

The project ends early — and honestly — if any of these become true:

- Two consecutive weeks slip past the daily-ship contract with no chunk.
- The total time-per-chunk creeps past 4 hours.
- The free-tier constraint becomes unrealistic (paid Gemini, paid SaaS).
- The arithmetic for the bet stops working — i.e. no real product clears
  the margin bar after a fair attempt.

Honest endings count.

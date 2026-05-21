---
title: "Margeen, day 1: 40 days of building an LLM that hunts margin in public"
date: 2026-05-21
slug: margeen-01-manifesto
reading_time: 9 min
---

# Margeen, day 1: 40 days of building an LLM that hunts margin in public

I am going to give a language model one sentence, and ask it to make money.

> *"I want to buy blue kids pants and re-sell them. I need >15% margin."*

That's it. That's the whole user interface. The model — running on a free
tier of Gemini Flash, on free SaaS, against a real Shopify store — has to
take that sentence and turn it into something a real person can buy from a
real URL, drop-shipped from a real supplier. With a real margin you could
defend in a real spreadsheet.

If that sounds like an arbitrage app you've read about — it kind of is.
Drop-shipping has been a thing for a decade. The agent angle isn't new
either; everyone is wiring LLMs to APIs. What's new here is the *budget*: a
free model, free tools, and a 40-day shipping contract that runs in public.
No "we'll demo it at the keynote." Daily chunks, daily blog, daily code
push, daily X and LinkedIn. If it fails, it fails on camera.

This first post is the manifesto. The bet, the rules, the supplier choice,
the 40-chunk arc, the kill criteria. So that when something breaks two
weeks from now you can pull this up and see exactly what we agreed to.

![A market stall: a stack of decorative plates next to a pile of assorted
objects](../../assets/01-flea-market.jpg)
*The job, summarised. A human at a flea market does this with their eyes —
glance at a pile, decide what's worth carrying home, price it, put it on a
table. Margeen is just that loop, in code, against AliExpress. Photo by
Melanie Chan on Unsplash.*

---

## The bet

Three claims, in order of decreasing comfort:

1. **A free LLM is good enough to surface candidate products.** Gemini
   Flash, GPT-4o-mini, Claude Haiku — they are all over the bar for "given
   a niche, name 50 plausible products." The work isn't the language; it's
   the wiring.
2. **A free SaaS stack is enough to run the whole loop.** Shopify dev store
   (free), Google AI Studio (free tier, generous), GitHub (free), a free
   workflow tool (Activepieces or self-hosted n8n). Hosting via the
   Hetzner box we already have, no incremental cost.
3. **The arithmetic works.** A 15%+ landed-margin product *does* exist on
   AliExpress for plenty of niches. The hard part isn't finding the SKU;
   it's costing it out honestly — and that's exactly what an agent can do
   without getting bored.

I expect to be wrong about at least one of these. The point of doing it in
public is that you will see exactly *which* one and how the bet adjusts.

---

## Why this is being built in public

I have a quiet selfish reason. Two networks I should be on more — X and
LinkedIn — only reward people who show up daily with something honest.
Margeen is the excuse. Forty articles, forty posts, forty days I have to
make something demonstrable. If the project is useful, great. If it just
forces me to ship every day for two months, also great.

Build-in-public also has a less selfish effect: it changes the work. You
cannot quietly take a shortcut when the shortcut has to be in the post. You
cannot quietly abandon a thread when the thread has its own URL. The
default failure mode of side projects is silence; daily posting is the
fix.

---

## Why AliExpress, not Temu (yet)

A drop-ship agent needs a supplier API. Three options were on the table:

- **Temu.** Has no usable open API. Code that talks to Temu either scrapes
  the public site (fragile, ToS-grey) or uses an affiliate broker (extra
  layer, extra fees, often gated to Chinese tax IDs). Bad foundation for an
  open-source project.
- **Shopee.** Real API, but invite-only for most regions, and the catalogue
  skews to South-East Asia in ways that don't map to the Western buyers
  Margeen is for.
- **AliExpress.** Has had an open platform for *years*. DSers, which
  Shopify itself recommends for drop-ship, talks to it natively. The
  catalogue is enormous, the shipping infrastructure is mature, and the
  same arbitrage math that works on Temu works here.

So Margeen's working supplier is **AliExpress**. Temu, Shopee, CJ
Dropshipping, and 1688 still get airtime — every chunk where it matters,
they'll be named, compared, and (in a later chunk) hit with an adapter-
shaped stub so a contributor can plug them in. But the day-one pipeline
runs on AliExpress.

This is also a deliberate honesty signal. "AI agent for Temu" sounds
sexier on a launch tweet. It would also be lying. If the agent can't ship
a real listing because the supplier API is fictional, the whole project is
a tech demo.

---

## What "free" actually means here

The constraint is "free of charge", and I want to spell out what that does
and doesn't allow.

**Allowed and used:**

- **Gemini 2.5 Flash** via Google AI Studio — generous free tier, fine for
  bursty work.
- **Shopify Partners dev store** (`wiswes2.myshopify.com`) — costs nothing,
  full API access, cannot take real payments. That last part is fine: most
  buyer-facing tests use shadow checkouts.
- **GitHub free** for code, **Cloudflare Pages / Vercel hobby** if a
  static surface is ever needed.
- **A free workflow tool** when the chunks need orchestration: most
  likely [Activepieces](https://www.activepieces.com/) (open-source n8n
  competitor) or self-hosted n8n on the Hetzner box.

**Allowed but only if needed:**

- A few dollars in real shipping cost when a chunk literally requires
  buying a product end-to-end. Drop-ship is "ship from supplier", but I
  want at least one chunk where a parcel really arrives.

**Not allowed:**

- Paid OpenAI / Anthropic / Gemini Pro. Not because they're bad — they're
  great — but because the whole "can amateurs do this?" bar means the
  model must be the free one. If a chunk genuinely needs a stronger
  model, that becomes a *finding* of the experiment, not a workaround.

---

## How the daily chunks work

Every chunk has the same shape. If a chunk doesn't hit all four bullets, it
isn't done.

- **An article**, ≤10 min read, on
  `wiswes.com/blog/margeen-project/<slug>`. The article is the *primary*
  artifact, not a write-up of one. The week one me will not let a chunk
  exist that I haven't explained to a stranger.
- **Code or notes**, pushed to this repo under `chunks/NN/`. Either real
  code, or a markdown design doc when the chunk is honest-to-god a doc
  chunk.
- **A short post on X and on LinkedIn**, written by hand. Each links the
  article and includes one image. (No threads, no carousels. If the
  article matters, the link matters.)
- **A new row in the daily log table** in this repo's `README.md`.

Roughly speaking, half the 40 chunks are code, half are docs. The doc
chunks are not filler — they're where the bet gets tested. "Should we
build local stockpile when a SKU breaks $X/day?" is not code; it's a
spreadsheet and an argument, and it has to be made before anything gets
built.

---

## The 40-chunk arc (TL;DR)

The full plan lives in [`docs/PLAN.md`](../../docs/PLAN.md). The shape is
four phases:

- **Phase 1 — chunks 1–8 — Manifesto & foundation.** The bet, the
  arithmetic, the supplier choice, the Gemini and Shopify wiring, the
  product schema, and a first manual end-to-end on a fake sync.
- **Phase 2 — chunks 9–20 — MVP.** Real AliExpress data, real Shopify
  listings, real human-in-the-loop approval, real margin math.
- **Phase 3 — chunks 21–32 — Demand-aware and honest.** Reorder
  triggers, support, batching, supplier compare, paid-ads economics,
  killing duds, drop-ship disclosures, articulated local stockpile.
- **Phase 4 — chunks 33–40 — Growth and post-mortem.** Real sales,
  failures, "would I run this for real?", open-sourcing the playbook,
  external PRs, and an honest ending.

If a chunk slot in the plan turns out to be wrong, it gets reordered or
dropped in public — not silently rewritten to match what I ended up
doing. The plan is the contract.

---

## Kill criteria

Build-in-public also means kill-in-public. The project ends early —
honestly — if any of these become true:

- Two consecutive weeks slip past the daily-ship contract with no chunk.
- A single chunk creeps past four hours of work.
- The free-tier constraint becomes unrealistic and we'd need a paid
  Gemini / Anthropic / OpenAI to make the agent work at all.
- The arithmetic stops working — i.e. after a fair attempt, no real
  product on AliExpress clears the 15%-landed-margin bar in any
  meaningful niche.

The fourth one is the interesting one. If the bet is wrong, that's a
finding, not a failure. The honest ending of "I tried, the margin isn't
there, and here is what I learned" is worth more than a half-built app
that quietly stops getting commits.

---

## What's in this chunk

Day-1 deliverables — the minimum that makes the rules above real:

- This article, published at
  `wiswes.com/blog/margeen-project/margeen-01-manifesto`.
- A bootstrapped `github.com/wiswes/margeen` repo: `README.md` (the pitch
  + daily log table), `LICENSE` (MIT), `.gitignore`, `docs/PLAN.md` (the
  40-chunk index), and this chunk's notes under `chunks/01/`.
- One X post and one LinkedIn post, written by hand and posted by hand.

No agent code yet. The agent shows up in Chunk 4.

---

## How to follow

- **GitHub** — every chunk pushes to
  [`github.com/wiswes/margeen`](https://github.com/wiswes/margeen).
- **Blog** — long-form lives at
  [`wiswes.com/blog/margeen-project`](https://wiswes.com/blog/margeen-project).
- **X / LinkedIn** — short version, posted by hand.

Day 2 is "the arithmetic of margin: why 15% almost never means 15%."

See you tomorrow.

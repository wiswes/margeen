# Margeen

> An LLM that hunts margin, in public. 40 chunks, one a day.

Margeen is a build-in-public experiment: can a small autonomous agent —
running on a *free* model and *free* SaaS — find resellable products with a
real positive margin, list them on a real Shopify store, and drop-ship them
to a real customer?

## The premise

Give the agent a sentence. A real one:

> *"I want to buy blue kids pants and re-sell them. I need >15% margin."*

It should:

1. **Find** candidate products on AliExpress (and rival marketplaces) that
   match the brief.
2. **Cost them out** — landed cost, fees, shipping, refunds, ad-cost — and
   compute *real* margin, not catalogue margin.
3. **Ask you** to approve the shortlist.
4. **List** the approved products on a Shopify dev store.
5. **Drop-ship** them when an order comes in.
6. **Watch the numbers** — kill duds, escalate winners.

If demand for a SKU crosses a threshold, the agent should *articulate* (not
build) a local-stockpile plan for the country we're selling in.

## The constraints

| Constraint | Why |
|---|---|
| **Free model only** — Gemini Flash | The "can amateurs do this?" bar |
| **Free SaaS only** | Same — must be reproducible with zero spend |
| **Shopify dev store** | No card, no risk to a live brand |
| **One chunk per day, public** | Forces shipping. Forces honesty. |
| **Article ≤ 10 min** | If I need longer, the chunk is too big |

## Why AliExpress, not Temu

Temu does not expose a usable public API and the scraping path is fragile
and ToS-grey. AliExpress has had an open platform for years; DSers and
similar agents drop-ship from it natively. The arbitrage economics are
similar enough that Margeen will work the same way against AliExpress, and
the code stays clean.

Temu, Shopee, CJ Dropshipping, and 1688 get *named* in chunks and get
adapter-shaped stubs — but AliExpress is the working supplier.

## The 40-chunk plan

See [`docs/PLAN.md`](docs/PLAN.md).

## How to follow

- **GitHub** — this repo. Every chunk pushes here.
- **Blog** — long-form articles live at
  [wiswes.com/blog/margeen-project](https://wiswes.com/blog/margeen-project).
- **X / LinkedIn** — short version of each chunk, by hand.

## Daily log

| Day | Chunk | Title | Date |
|---|---|---|---|
| 1 | 01 | Manifesto — 40 days of building an LLM that hunts margin in public | 2026-05-21 |

## License

MIT. See [`LICENSE`](LICENSE).

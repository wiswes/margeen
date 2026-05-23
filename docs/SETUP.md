# Margeen — Day 1 setup

How to wire the "prompt in Shopify → search runs in GitHub Actions" loop.
Everything below is free.

```
[ You add a draft product in Shopify ]
                │
                │  Shopify Flow watches: product created + tag = margeen-search
                ▼
[ HTTP POST → api.github.com/repos/wiswes/margeen/dispatches ]
                │
                │  event_type = "margeen_search", client_payload = { prompt }
                ▼
[ GitHub Actions workflow runs scripts/search_aliexpress.py ]
                │
                │  Commits candidates/{ts}_{slug}.json back to the repo
                ▼
[ You read the JSON in the repo ]
```

## 1. Generate a GitHub Personal Access Token (PAT)

Shopify needs a token to talk to GitHub.

1. Open <https://github.com/settings/personal-access-tokens/new>
2. Token name: `margeen-shopify-dispatch`
3. Resource owner: your account (the one that owns `wiswes/margeen`)
4. Expiration: anything ≥ 90 days
5. Repository access: **Only select repositories** → `wiswes/margeen`
6. Repository permissions:
   - **Contents: Read and write**
   - **Metadata: Read**
   - **Actions: Read and write**
7. Click **Generate token** and **copy it once** — you can't read it
   again afterwards.

Keep this token somewhere safe (1Password, etc.). It is the only secret
Shopify needs to know.

## 2. Test the workflow manually first

Before wiring Shopify, confirm the workflow runs from GitHub itself:

1. Go to <https://github.com/wiswes/margeen/actions/workflows/search.yml>
2. Click **Run workflow**.
3. Enter a prompt, e.g. `blue kids pants`.
4. Click **Run workflow**.

After ~20–40 seconds a new commit appears on `main` with the file
`candidates/{timestamp}_{slug}.json`. Open it.

If `blocked: true` shows up, AliExpress served a bot-detection page —
that is the known limitation the Day-1 article calls out. The wire
still works; the *data source* is the next chunk's problem.

## 3. Wire Shopify Flow

This step happens entirely inside your Shopify admin. It needs Shopify
Flow, which is free on every Shopify plan since 2022.

1. In Shopify admin, open **Apps → Shopify Flow → Create workflow**.
2. **Trigger:** `Product created`.
3. **Condition:** `Product / Tags / contains / margeen-search`.
4. **Action:** `Send HTTP request`.
   - URL: `https://api.github.com/repos/wiswes/margeen/dispatches`
   - Method: `POST`
   - Headers:
     - `Authorization: Bearer <PAT from step 1>`
     - `Accept: application/vnd.github+json`
     - `X-GitHub-Api-Version: 2022-11-28`
     - `User-Agent: shopify-flow-margeen`
   - Body (JSON):
     ```json
     {
       "event_type": "margeen_search",
       "client_payload": {
         "prompt": "{{ product.title }}",
         "product_id": "{{ product.id }}"
       }
     }
     ```
5. **Activate** the workflow.

## 4. Fire one for real

1. Shopify admin → **Products → Add product**.
2. Title: the product category or short description you want Margeen
   to search, e.g. `Blue kids pants` or `Wireless earbuds with case`.
   (Margin and pricing are not part of the Day-1 prompt yet — that
   arrives in a later chunk.)
3. **Status: Draft** (do not publish — this is just a trigger).
4. Tag: `margeen-search`.
5. Save.

Within ~10–30 seconds:

- Shopify Flow fires the HTTP request.
- GitHub Actions queues the workflow.
- `scripts/search_aliexpress.py` runs.
- A new commit lands on `main` with the candidates JSON.

If nothing happens, check:

- Shopify Flow's run history (any failed HTTP requests).
- GitHub Actions tab (any failed runs).
- The PAT hasn't expired.

## 5. Day-1 limitations (the honest list)

- **AliExpress bot-detection.** The free direct-curl path is reliably
  blocked from data-centre IPs. Chunk 03 picks a real data source
  (RapidAPI free tier, ScraperAPI, or the AliExpress Open Platform).
- **No price extraction yet.** The script only pulls product ID, URL,
  and title. Margin maths arrives with chunk 04.
- **No Shopify side-effects yet.** Margeen doesn't push anything back
  into Shopify on Day 1. That arrives with chunk 05 (publish to
  Shopify Admin API).
- **Draft product as the prompt UI is a hack.** A proper embedded
  Shopify app comes much later. For now it works on every Shopify
  plan with zero code.

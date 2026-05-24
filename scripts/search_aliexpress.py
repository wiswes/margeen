"""Margeen search: turn a one-sentence prompt into a list of
AliExpress candidate products.

Pipeline (current):
  1. expand_keywords(prompt) → ~25 search-variant queries via Gemini Flash.
     If GEMINI_API_KEY isn't set the script falls back to [prompt] so a
     fork of this repo without a key still works (same behaviour as Day 2).
  2. For each variant, fetch the AliExpress search page via curl in
     parallel (ThreadPoolExecutor).
  3. Parse product cards out of each response with regex; dedupe across
     variants by product_id.
  4. Write the result as JSON under candidates/{ts}_{slug}.json.

Why curl and regex: see chunk 2 of the build journal. Short version —
Python requests gets bot-blocked by AliExpress (TLS fingerprint), and the
search results are rendered server-side as plain HTML.

Known limitations (the build-in-public risks this chunk's article calls out):
- Relevance is not filtered yet. Expansion gives more candidates, but
  some will be off-topic; an LLM relevance check is chunk 4.
- AliExpress can serve a bot-detection page to data-centre IPs. If a
  variant gets blocked the script records it in `variants[].blocked` and
  keeps going with the rest.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib import error as urllib_error, request as urllib_request
from urllib.parse import quote_plus

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# Lightweight bot-block markers — if any of these dominate the response the
# page is a captcha / login wall, not a real search result.
BOT_BLOCK_MARKERS = (
    "/_____tmd_____/punish",
    "Slider Verification",
    "abnormal-request",
    "captcha_session_id",
)

# How many past searches to keep in candidates/. Anything older gets
# pruned on every run so the folder does not flood across 40 chunks.
KEEP_RECENT = 10

# Keyword expansion limits — chosen so a worst-case run stays under a
# minute on a GitHub Actions runner.
GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    f"{GEMINI_MODEL}:generateContent"
)
MAX_VARIANTS = 25
MAX_PARALLEL_FETCHES = 8


def prune_candidates(out_dir: Path) -> None:
    """Keep the N most recent timestamped search results; delete the rest.

    `latest.json` and `.gitkeep` are always kept. Files are grouped by their
    `YYYYMMDDTHHMMSSZ_` prefix so a JSON and its `.debug.html` counterpart
    are evicted together.
    """
    ts_re = re.compile(r"^(\d{8}T\d{6}Z)_")
    grouped: dict[str, list[Path]] = {}
    for p in out_dir.iterdir():
        if not p.is_file() or p.name in ("latest.json", ".gitkeep"):
            continue
        m = ts_re.match(p.name)
        if not m:
            continue
        grouped.setdefault(m.group(1), []).append(p)
    keep = set(sorted(grouped.keys(), reverse=True)[:KEEP_RECENT])
    for ts, files in grouped.items():
        if ts in keep:
            continue
        for p in files:
            print(f"[margeen] pruning {p.name}")
            p.unlink()


def slugify(text: str, max_len: int = 40) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower())
    s = s.strip("-")
    return s[:max_len] or "search"


def expand_keywords(prompt: str, timeout: int = 20) -> list[str]:
    """Ask Gemini Flash to fan a single prompt into ~25 search variants.

    Returns a list that always starts with the original prompt — so if
    expansion silently fails (no key, API error, bad JSON) the caller
    still gets the Day-2 single-variant behaviour for free.

    The script intentionally does not hard-fail on a missing key: this
    repo is public and any fork should be able to `Run workflow` without
    a Google Cloud account.
    """
    base = [prompt]
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("[margeen] GEMINI_API_KEY not set — skipping expansion")
        return base

    user_prompt = (
        f'Generate up to {MAX_VARIANTS} short AliExpress search-query '
        f'variants a shopper might type to find this: "{prompt}".\n\n'
        "Rules:\n"
        "- Each variant 1–5 words, lowercase, no punctuation.\n"
        "- Include synonyms, common misspellings, sibling categories, "
        "brand-name variants.\n"
        "- No questions, no sentences, no duplicates of the original.\n"
        "- Return ONLY a JSON array of strings. No prose, no code fence."
    )
    body = json.dumps({
        "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "responseMimeType": "application/json",
        },
    }).encode("utf-8")
    req = urllib_request.Request(
        f"{GEMINI_ENDPOINT}?key={api_key}",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib_request.urlopen(req, timeout=timeout) as r:
            response = json.loads(r.read().decode("utf-8"))
    except (urllib_error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"[margeen] expansion API error: {e} — falling back to single variant")
        return base

    try:
        text = response["candidates"][0]["content"]["parts"][0]["text"]
        raw = json.loads(text)
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        print(f"[margeen] expansion parse error: {e} — falling back")
        return base

    if not isinstance(raw, list):
        print("[margeen] expansion did not return a list — falling back")
        return base

    # Normalise: lowercase, strip, drop empties + the original (we re-add
    # it at the head so it's always variant #0 in the output).
    seen: set[str] = set()
    cleaned: list[str] = []
    for item in raw:
        if not isinstance(item, str):
            continue
        v = re.sub(r"\s+", " ", item).strip().lower()
        if not v or v == prompt.lower() or v in seen:
            continue
        cleaned.append(v)
        seen.add(v)
    print(f"[margeen] expansion: {len(cleaned)} variants from LLM")
    return base + cleaned[: MAX_VARIANTS - 1]


def fetch(prompt: str, timeout: int = 30) -> tuple[int, str]:
    """Fetch the AliExpress search page via curl.

    We shell out to curl on purpose: the Python `requests` library has a
    different TLS / HTTP fingerprint than browsers and AliExpress serves
    it a bot-detection page. curl's fingerprint passes through to a real
    search HTML response. curl is preinstalled on every GitHub Actions
    runner so no extra setup is needed.
    """
    url = (
        "https://www.aliexpress.com/wholesale?SearchText="
        f"{quote_plus(prompt)}"
    )
    cmd = [
        "curl",
        "-sSL",
        "--max-time", str(timeout),
        "-A", USER_AGENT,
        "-H", "Accept-Language: en-US,en;q=0.9",
        "-H", (
            "Accept: text/html,application/xhtml+xml,application/xml;q=0.9,"
            "image/avif,image/webp,*/*;q=0.8"
        ),
        "-w", "\n__HTTP_STATUS__:%{http_code}",
        url,
    ]
    result = subprocess.run(
        cmd, capture_output=True, text=True, check=False
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"curl failed (exit {result.returncode}): {result.stderr.strip()}"
        )
    body = result.stdout
    # The HTTP status code is appended to stdout by our -w flag.
    m = re.search(r"\n__HTTP_STATUS__:(\d+)\s*$", body)
    if not m:
        return 0, body
    status = int(m.group(1))
    body = body[: m.start()]
    return status, body


def looks_blocked(html_body: str) -> bool:
    if len(html_body) < 5000:
        return True
    return any(marker in html_body for marker in BOT_BLOCK_MARKERS)


def parse_items(html_body: str) -> list[dict]:
    items: list[dict] = []
    seen: set[str] = set()
    # Find each product card. AliExpress search items expose
    # href="//www.aliexpress.<tld>/item/<id>.html..." with a title nearby.
    # The TLD varies: US visitors (including GitHub Actions runners) are
    # geo-routed to aliexpress.us; EU/global hits aliexpress.com. Match
    # any TLD on the aliexpress domain.
    pattern = re.compile(
        r'href="(//(?:www\.)?aliexpress\.[a-z]{2,3}/item/(\d+)\.html[^"]*)"[^>]*>'
    )
    # First "$X.YY" or "US $X.YY" we see inside a product chunk is the
    # listed price. There can be a few price spans (current, original,
    # sku-coupon); the first one is what the user sees as the headline.
    price_pat = re.compile(r'(?:US ?\$|\$)\s?([0-9]+(?:[.,][0-9]{1,2})?)')
    for m in pattern.finditer(html_body):
        pid = m.group(2)
        if pid in seen:
            continue
        url = "https:" + m.group(1).split("?")[0]
        chunk = html_body[m.end():m.end() + 3500]
        title_m = re.search(r'title="([^"]{10,250})"', chunk)
        title = html.unescape(title_m.group(1)) if title_m else None
        price_m = price_pat.search(chunk)
        price_str = price_m.group(0) if price_m else None
        price_value = None
        if price_m:
            try:
                price_value = float(price_m.group(1).replace(",", "."))
            except ValueError:
                price_value = None
        items.append({
            "product_id": pid,
            "url": url,
            "title": title,
            "price_str": price_str,
            "price_usd": price_value,
        })
        seen.add(pid)
    return items


def search_variant(variant: str) -> dict:
    """Fetch + parse a single search variant. Always returns a record;
    errors become record fields, never raised, so one bad variant doesn't
    take the whole run down.
    """
    record: dict = {
        "keyword": variant,
        "http_status": 0,
        "response_bytes": 0,
        "blocked": False,
        "items": [],
        "error": None,
    }
    try:
        status, body = fetch(variant)
    except Exception as e:
        record["error"] = str(e)
        return record
    record["http_status"] = status
    record["response_bytes"] = len(body)
    record["blocked"] = looks_blocked(body)
    if not record["blocked"]:
        record["items"] = parse_items(body)
    return record


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="The search prompt, e.g. 'blue kids pants'")
    parser.add_argument(
        "--out-dir",
        default="candidates",
        help="Directory to write JSON results (default: candidates/)",
    )
    parser.add_argument(
        "--no-expand",
        action="store_true",
        help="Skip LLM keyword expansion; search only the original prompt.",
    )
    args = parser.parse_args()

    print(f"[margeen] argv: {sys.argv!r}", file=sys.stderr)
    prompt = args.prompt.strip()
    if not prompt:
        print("ERROR: empty prompt (after strip)", file=sys.stderr)
        return 2

    print(f"[margeen] searching AliExpress for: {prompt!r}")

    if args.no_expand:
        variants = [prompt]
    else:
        variants = expand_keywords(prompt)
    print(f"[margeen] fetching {len(variants)} variant(s) "
          f"(up to {MAX_PARALLEL_FETCHES} in parallel)")

    # Fetch + parse all variants in parallel. as_completed keeps memory
    # bounded; we just need the records, the original order doesn't
    # matter (we sort by keyword at the end for stable JSON).
    records: list[dict] = []
    with ThreadPoolExecutor(max_workers=MAX_PARALLEL_FETCHES) as pool:
        futures = {pool.submit(search_variant, v): v for v in variants}
        for fut in as_completed(futures):
            records.append(fut.result())
    records.sort(key=lambda r: r["keyword"])

    # Flatten to a unique candidate list. First occurrence of each
    # product_id wins; we add `seen_in` so the audit log shows which
    # variant(s) surfaced that product.
    candidates: list[dict] = []
    by_pid: dict[str, dict] = {}
    for rec in records:
        for item in rec["items"]:
            pid = item["product_id"]
            existing = by_pid.get(pid)
            if existing is None:
                copy = dict(item)
                copy["seen_in"] = [rec["keyword"]]
                by_pid[pid] = copy
                candidates.append(copy)
            else:
                existing["seen_in"].append(rec["keyword"])

    # Drop `items` from per-variant records — the flat candidates list is
    # what consumers want; the records are kept for the audit trail
    # (which variant returned how many, which was blocked, etc).
    variant_summaries = [
        {k: v for k, v in rec.items() if k != "items"}
        | {"candidate_count": len(rec["items"])}
        for rec in records
    ]
    blocked_count = sum(1 for v in variant_summaries if v["blocked"])
    error_count = sum(1 for v in variant_summaries if v["error"])
    all_blocked = blocked_count == len(variant_summaries) and len(variant_summaries) > 0
    print(f"[margeen] parsed {len(candidates)} unique candidates "
          f"across {len(variants)} variants "
          f"({blocked_count} blocked, {error_count} errored)")

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ts}_{slugify(prompt)}.json"

    payload = {
        "schema": "margeen.search/v2",
        "timestamp": ts,
        "prompt": prompt,
        "source": "aliexpress",
        "expansion": {
            "enabled": not args.no_expand,
            "model": GEMINI_MODEL if not args.no_expand else None,
            "variant_count": len(variants),
        },
        "blocked": all_blocked,
        "candidate_count": len(candidates),
        "variants": variant_summaries,
        "candidates": candidates,
    }
    serialised = json.dumps(payload, ensure_ascii=False, indent=2)
    out_path.write_text(serialised)
    print(f"[margeen] wrote {out_path}")

    # Stable pointer to the most recent search — overwritten every run.
    # Lets anyone link to a single URL for "the latest result".
    latest_path = out_dir / "latest.json"
    latest_path.write_text(serialised)
    print(f"[margeen] also updated {latest_path}")

    # Debug aid: when every variant came up blocked, save the raw body
    # of the first one so we can inspect what AliExpress actually
    # served. Single-variant runs (--no-expand or no key) also benefit.
    if all_blocked or not candidates:
        try:
            _, dbg_body = fetch(variants[0])
            debug_path = out_dir / f"{ts}_{slugify(prompt)}.debug.html"
            debug_path.write_text(dbg_body, encoding="utf-8")
            print(f"[margeen] no candidates — saved raw body to {debug_path}")
        except Exception as e:
            print(f"[margeen] could not save debug body: {e}", file=sys.stderr)

    # Tidy up — keep candidates/ from flooding across daily runs.
    prune_candidates(out_dir)

    # Don't fail the workflow when blocked — the JSON record is the finding.
    return 0


if __name__ == "__main__":
    sys.exit(main())

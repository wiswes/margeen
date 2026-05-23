"""Day-1 Margeen search: turn a one-sentence prompt into a list of
AliExpress candidate products.

Super-simple v1:
- One HTTP GET to the public AliExpress search page.
- Regex-extracts product ID, URL, and title from the rendered HTML.
- Writes the result as JSON under candidates/{ts}_{slug}.json.

Known limitations (the build-in-public risks the day-1 article calls out):
- Prices are not extracted yet. The prompt is just a category /
  description on Day 1 — margin and pricing come in a later chunk.
- AliExpress can serve a bot-detection page to data-centre IPs (GitHub
  Actions runs on Azure). If that happens, the script exits with a clear
  "blocked" finding instead of writing garbage data.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt", help="The search prompt, e.g. 'blue kids pants'")
    parser.add_argument(
        "--out-dir",
        default="candidates",
        help="Directory to write JSON results (default: candidates/)",
    )
    args = parser.parse_args()

    print(f"[margeen] argv: {sys.argv!r}", file=sys.stderr)
    prompt = args.prompt.strip()
    if not prompt:
        print("ERROR: empty prompt (after strip)", file=sys.stderr)
        return 2

    print(f"[margeen] searching AliExpress for: {prompt!r}")
    try:
        status, body = fetch(prompt)
    except Exception as e:
        print(f"[margeen] fetch error: {e}", file=sys.stderr)
        return 3

    print(f"[margeen] HTTP {status}, {len(body)} bytes")

    blocked = looks_blocked(body)
    items = [] if blocked else parse_items(body)
    print(f"[margeen] parsed {len(items)} candidate products"
          + (" (BLOCKED)" if blocked else ""))

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{ts}_{slugify(prompt)}.json"

    payload = {
        "schema": "margeen.search/v1",
        "timestamp": ts,
        "prompt": prompt,
        "source": "aliexpress",
        "http_status": status,
        "response_bytes": len(body),
        "blocked": blocked,
        "candidate_count": len(items),
        "candidates": items,
    }
    serialised = json.dumps(payload, ensure_ascii=False, indent=2)
    out_path.write_text(serialised)
    print(f"[margeen] wrote {out_path}")

    # Stable pointer to the most recent search — overwritten every run.
    # Lets anyone link to a single URL for "the latest result".
    latest_path = out_dir / "latest.json"
    latest_path.write_text(serialised)
    print(f"[margeen] also updated {latest_path}")

    # Debug aid: when we got nothing useful, save the raw response body
    # alongside the JSON so we can inspect what AliExpress actually
    # served. This is how we tell "bot block" from "JS-only page" from
    # "geo interstitial".
    if not items:
        debug_path = out_dir / f"{ts}_{slugify(prompt)}.debug.html"
        debug_path.write_text(body, encoding="utf-8")
        print(f"[margeen] no candidates — saved raw body to {debug_path}")

    # Tidy up — keep candidates/ from flooding across daily runs.
    prune_candidates(out_dir)

    # Don't fail the workflow when blocked — the JSON record is the finding.
    return 0


if __name__ == "__main__":
    sys.exit(main())

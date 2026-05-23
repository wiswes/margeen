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
    # href="//www.aliexpress.com/item/<id>.html..." with a title nearby.
    pattern = re.compile(
        r'href="(//www\.aliexpress\.com/item/(\d+)\.html[^"]*)"[^>]*>'
    )
    for m in pattern.finditer(html_body):
        pid = m.group(2)
        if pid in seen:
            continue
        url = "https:" + m.group(1).split("?")[0]
        chunk = html_body[m.end():m.end() + 3500]
        title_m = re.search(r'title="([^"]{10,250})"', chunk)
        title = html.unescape(title_m.group(1)) if title_m else None
        items.append({
            "product_id": pid,
            "url": url,
            "title": title,
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

    prompt = args.prompt.strip()
    if not prompt:
        print("ERROR: empty prompt", file=sys.stderr)
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
        "blocked": blocked,
        "candidate_count": len(items),
        "candidates": items,
    }
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"[margeen] wrote {out_path}")

    # Don't fail the workflow when blocked — the JSON record is the finding.
    return 0


if __name__ == "__main__":
    sys.exit(main())

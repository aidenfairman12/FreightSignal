"""
fetch_articles.py — Pull fresh articles from logistics/trade RSS feeds.

Runs every 6 hours via GitHub Actions. New articles are deduplicated against
the existing raw article store by URL, then written to data/raw/articles.jsonl.

Sources chosen for coverage + public RSS availability:
  - FreightWaves           https://www.freightwaves.com/feed
  - Supply Chain Dive      https://www.supplychaindive.com/feeds/news/
  - DC Velocity            https://www.dcvelocity.com/rss/
  - Journal of Commerce    https://www.joc.com/rss/
  - Splash247              https://splash247.com/feed/
"""

import hashlib
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path

import feedparser
import httpx

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ── Paths ──────────────────────────────────────────────────────────────────
ROOT       = Path(__file__).parent.parent
RAW_DIR    = ROOT / "data" / "raw"
ARTICLES_F = RAW_DIR / "articles.jsonl"

RAW_DIR.mkdir(parents=True, exist_ok=True)

# ── RSS feed sources ───────────────────────────────────────────────────────
FEEDS = [
    {
        "name": "FreightWaves",
        "url":  "https://www.freightwaves.com/feed",
        "tags": ["freight", "trucking", "rail", "ocean"],
    },
    {
        "name": "Supply Chain Dive",
        "url":  "https://www.supplychaindive.com/feeds/news/",
        "tags": ["supply-chain", "logistics", "retail"],
    },
    {
        "name": "DC Velocity",
        "url":  "https://www.dcvelocity.com/rss/",
        "tags": ["warehousing", "distribution", "logistics"],
    },
    {
        "name": "Journal of Commerce",
        "url":  "https://www.joc.com/rss/",
        "tags": ["ocean", "ports", "intermodal", "trade"],
        "min_content_len": 50,
    },
    {
        "name": "Splash247",
        "url":  "https://splash247.com/feed/",
        "tags": ["trade", "economy", "shipping", "maritime"],
    },
]

# Minimum article body length to keep (filters out link-only RSS entries)
MIN_CONTENT_LEN = 100


def _url_id(url: str) -> str:
    """Stable short ID for deduplication — SHA256 of the URL."""
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def load_existing_ids() -> set[str]:
    """Return the set of article IDs already in articles.jsonl."""
    if not ARTICLES_F.exists():
        return set()
    ids = set()
    with open(ARTICLES_F) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    ids.add(json.loads(line)["id"])
                except (json.JSONDecodeError, KeyError):
                    pass
    return ids


def fetch_feed(feed: dict, existing_ids: set[str]) -> list[dict]:
    """Fetch and parse one RSS feed. Returns new articles only."""
    name = feed["name"]
    logger.info(f"Fetching {name}...")

    try:
        # feedparser handles redirects and encoding — use httpx for timeout control
        resp = httpx.get(feed["url"], timeout=20, follow_redirects=True,
                         headers={"User-Agent": "FreightSignal-Bot/1.0"})
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
    except Exception as exc:
        logger.warning(f"  {name}: fetch failed — {exc}")
        return []

    new_articles = []
    for entry in parsed.entries:
        url = entry.get("link", "")
        if not url:
            continue

        article_id = _url_id(url)
        if article_id in existing_ids:
            continue

        # Extract content — prefer summary_detail, fall back to summary
        content = ""
        if hasattr(entry, "content"):
            content = entry.content[0].get("value", "")
        elif hasattr(entry, "summary"):
            content = entry.summary

        # Strip HTML tags crudely (feedparser gives us HTML in many feeds)
        import re
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()

        if len(content) < feed.get("min_content_len", MIN_CONTENT_LEN):
            continue

        published_raw = entry.get("published", "") or entry.get("updated", "")
        try:
            import email.utils
            pub_dt = email.utils.parsedate_to_datetime(published_raw)
            published = pub_dt.astimezone(timezone.utc).isoformat()
        except Exception:
            published = datetime.now(timezone.utc).isoformat()

        new_articles.append({
            "id":        article_id,
            "source":    name,
            "tags":      feed["tags"],
            "title":     entry.get("title", "").strip(),
            "url":       url,
            "published": published,
            "content":   content,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        })

    logger.info(f"  {name}: {len(new_articles)} new articles")
    return new_articles


def main():
    existing_ids = load_existing_ids()
    logger.info(f"Existing article store: {len(existing_ids)} articles")

    all_new: list[dict] = []
    for feed in FEEDS:
        articles = fetch_feed(feed, existing_ids)
        all_new.extend(articles)
        # Be polite — short delay between feeds
        time.sleep(1.5)

    if not all_new:
        logger.info("No new articles found — store is up to date.")
        return

    # Append new articles to the JSONL store
    with open(ARTICLES_F, "a") as f:
        for article in all_new:
            f.write(json.dumps(article) + "\n")

    logger.info(f"Added {len(all_new)} new articles → {ARTICLES_F}")
    logger.info("Run chunk_embed.py to update the vector store.")


if __name__ == "__main__":
    main()

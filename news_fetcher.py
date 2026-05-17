import hashlib
from typing import Optional

import feedparser

# Free, no-auth RSS feeds — mix of sources for variety
RSS_FEEDS = {
    "BBC World":     "http://feeds.bbci.co.uk/news/world/rss.xml",
    "The Guardian":  "https://www.theguardian.com/world/rss",
    "Al Jazeera":    "https://www.aljazeera.com/xml/rss/all.xml",
    "NPR":           "https://feeds.npr.org/1001/rss.xml",
    "Reuters":       "https://feeds.reuters.com/reuters/topNews",
    "Hacker News":   "https://news.ycombinator.com/rss",
}


def _article_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:8]


def _clean_summary(text: str) -> str:
    """Strip HTML tags from RSS summaries."""
    import re
    return re.sub(r"<[^>]+>", "", text or "").strip()


def fetch_news(topic: Optional[str] = None, count: int = 5) -> list[dict]:
    """
    Pull articles from all RSS feeds, deduplicate, optionally filter by topic,
    and return the top `count` results.
    """
    articles = []
    seen_urls: set[str] = set()

    for source_name, feed_url in RSS_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:15]:
                url = entry.get("link", "")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)

                summary = _clean_summary(
                    entry.get("summary", entry.get("description", ""))
                )
                articles.append({
                    "id":        _article_id(url),
                    "title":     entry.get("title", "").strip(),
                    "summary":   summary[:600],
                    "url":       url,
                    "source":    source_name,
                    "published": entry.get("published", ""),
                })
        except Exception as exc:
            print(f"[news] Failed to fetch {source_name}: {exc}")

    # Topic filtering: bubble matching articles to the top
    if topic:
        kw = topic.lower()
        articles.sort(
            key=lambda a: (
                kw in a["title"].lower() or kw in a["summary"].lower()
            ),
            reverse=True,
        )

    # Drop articles with empty titles
    articles = [a for a in articles if a["title"]]

    return articles[:count]

"""News scraper with RSS + HTML fallback — serverless version."""
import html
import logging
import re
import feedparser
import httpx
from lib.engine import generate_content, rank_articles, score_articles

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {"name": "גלובס נדל\"ן", "url": "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederNode?iID=585"},
    {"name": "TheMarker", "url": "https://www.themarker.com/cmlink/1.145"},
]

# HTML scraping sources (no working RSS)
HTML_SOURCES = [
    {
        "name": "מגדילים",
        "url": "https://www.magdilim.co.il",
        "title_pattern": r'<a[^>]*href="(https://(?:www\.)?magdilim\.co\.il/\d{6,}[^"]*)"[^>]*>([^<]{10,})</a>',
        "base_url": "",
        "html_unescape": True,
    },
]

# Strong keywords — one match is enough
STRONG_KEYWORDS = [
    "נדל\"ן", "נדלן", "דירה", "דירות", "משכנתא", "משכנתה", "פינוי בינוי",
    "תמ\"א", "תמא", "מחירי דיור", "שוק הדיור", "מחיר למשתכן",
    "התחדשות עירונית", "קבלן", "תיווך", "מתווך", "LTV",
    "מדד תשומות", "זכויות בנייה", "טאבו", "רישום מקרקעין",
]

# Weak keywords — need 2+ matches or 1 weak + context from title
WEAK_KEYWORDS = [
    "שכירות", "בנייה", "יזם", "יזמות", "ריבית", "פריים", "מינוף",
    "תשואה", "קרקע", "מגרש", "השקעה", "השקעות", "בניין", "דיור",
    "רכישה", "מכירה", "הון עצמי", "רוכשים", "קונים", "מוכרים",
]

ALL_KEYWORDS = STRONG_KEYWORDS + WEAK_KEYWORDS
REALESTATE_KEYWORDS = ALL_KEYWORDS  # backward compat


def _is_realestate(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    # One strong keyword is enough
    if any(kw in text for kw in STRONG_KEYWORDS):
        return True
    # For weak keywords, need at least 2 matches
    weak_count = sum(1 for kw in WEAK_KEYWORDS if kw in text)
    return weak_count >= 2


def _fetch_html_articles(source: dict, max_items: int = 5) -> list:
    """Scrape articles from HTML pages without RSS."""
    articles = []
    try:
        resp = httpx.get(source["url"], timeout=15, follow_redirects=True, headers={
            "User-Agent": "Mozilla/5.0 (compatible; KarnafBot/1.0)"
        })
        if resp.status_code != 200:
            return []
        matches = re.findall(source["title_pattern"], resp.text)
        for href, title in matches[:max_items]:
            title = html.unescape(title.strip()) if source.get("html_unescape") else title.strip()
            if not _is_realestate(title, ""):
                continue
            link = href if href.startswith("http") else source["base_url"] + href
            articles.append({
                "source": source["name"],
                "title": title,
                "link": link,
                "summary": "",
            })
    except Exception as e:
        logger.warning(f"שגיאה בסריקת {source['name']}: {e}")
    return articles


def fetch_latest_news(max_per_feed: int = 5) -> list:
    articles = []
    # RSS feeds
    for feed_info in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_info["url"])
            for entry in feed.entries[:max_per_feed]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:300]
                if not _is_realestate(title, summary):
                    continue
                articles.append({
                    "source": feed_info["name"],
                    "title": title,
                    "link": entry.get("link", ""),
                    "summary": summary,
                })
        except Exception as e:
            logger.warning(f"שגיאה בקריאת {feed_info['name']}: {e}")

    # HTML scraping sources
    for source in HTML_SOURCES:
        articles.extend(_fetch_html_articles(source, max_per_feed))

    return articles


def pick_hottest(articles: list) -> dict:
    """Pick single hottest article (legacy compat)."""
    if not articles:
        return None
    idx = rank_articles(articles)
    return articles[idx]


def pick_top_articles(articles: list, count: int = 3) -> list:
    """Score and return top N articles with engagement scores."""
    if not articles:
        return []
    scored = score_articles(articles)
    return scored[:count]

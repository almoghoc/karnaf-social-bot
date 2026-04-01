"""RSS news scraper with real-estate keyword filtering — serverless version."""
import logging
import feedparser
from lib.engine import generate_content, rank_articles

logger = logging.getLogger(__name__)

RSS_FEEDS = [
    {"name": "כלכליסט נדל\"ן", "url": "https://www.calcalist.co.il/GeneralRSS/0,16335,L-8,00.xml"},
    {"name": "ynet נדל\"ן", "url": "https://www.ynet.co.il/Integration/StoryRss1854.xml"},
    {"name": "מגדילים", "url": "https://www.magdilim.co.il/feed"},
    {"name": "מרכז הנדל\"ן", "url": "https://nadlancenter.co.il/feed"},
    {"name": "גלובס נדל\"ן", "url": "https://www.globes.co.il/webservice/rss/rssfeeder.asmx/FeederNode?iID=2507"},
]

REALESTATE_KEYWORDS = [
    "נדל\"ן", "נדלן", "דירה", "דירות", "משכנתא", "שכירות", "פינוי בינוי",
    "תמ\"א", "תמא", "מחירי דיור", "בנייה", "קבלן", "יזם", "יזמות",
    "התחדשות עירונית", "ריבית", "פריים", "מינוף", "תשואה", "קרקע",
    "מגרש", "תיווך", "מתווך", "השקעה", "השקעות", "בניין", "דיור",
    "מחיר למשתכן", "רכישה", "מכירה", "שוק הדיור", "מדד תשומות",
    "הון עצמי", "LTV", "משכנתה", "רוכשים", "קונים", "מוכרים",
]


def _is_realestate(title: str, summary: str) -> bool:
    text = f"{title} {summary}".lower()
    return any(kw in text for kw in REALESTATE_KEYWORDS)


def fetch_latest_news(max_per_feed: int = 5) -> list:
    articles = []
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
    return articles


def pick_hottest(articles: list) -> dict:
    if not articles:
        return None
    idx = rank_articles(articles)
    return articles[idx]

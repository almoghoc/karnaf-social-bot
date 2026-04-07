"""State management via Upstash Redis REST API — serverless compatible."""
import os
import json
import httpx

UPSTASH_URL = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")

HEADERS = {"Authorization": f"Bearer {UPSTASH_TOKEN}"}


def _redis_cmd(*args):
    """Execute a Redis command via Upstash REST API."""
    if not UPSTASH_URL:
        return None
    resp = httpx.post(UPSTASH_URL, headers=HEADERS, json=list(args), timeout=10)
    data = resp.json()
    return data.get("result")


def is_article_processed(url: str) -> bool:
    return bool(_redis_cmd("SISMEMBER", "processed_articles", url))


def mark_article_processed(url: str):
    _redis_cmd("SADD", "processed_articles", url)
    # Keep set bounded
    count = _redis_cmd("SCARD", "processed_articles")
    if count and int(count) > 200:
        _redis_cmd("SPOP", "processed_articles")
    _redis_cmd("SET", "last_post_time", json.dumps({"url": url}))


def is_post_commented(url: str) -> bool:
    return bool(_redis_cmd("SISMEMBER", "commented_posts", url))


def mark_post_commented(url: str):
    _redis_cmd("SADD", "commented_posts", url)
    count = _redis_cmd("SCARD", "commented_posts")
    if count and int(count) > 200:
        _redis_cmd("SPOP", "commented_posts")
    _redis_cmd("SET", "last_comment_time", json.dumps({"url": url}))


def get_pending_post():
    data = _redis_cmd("GET", "pending_post")
    return json.loads(data) if data else None


def set_pending_post(post_data: dict):
    _redis_cmd("SET", "pending_post", json.dumps(post_data, ensure_ascii=False))


def clear_pending_post():
    _redis_cmd("DEL", "pending_post")


def get_pending_comment():
    data = _redis_cmd("GET", "pending_comment")
    return json.loads(data) if data else None


def set_pending_comment(comment_data: dict):
    _redis_cmd("SET", "pending_comment", json.dumps(comment_data, ensure_ascii=False))


def clear_pending_comment():
    _redis_cmd("DEL", "pending_comment")


# --- Multi-platform pending ---

def set_pending_platforms(data: dict):
    """Store generated content for all platforms pending approval."""
    _redis_cmd("SET", "pending_platforms", json.dumps(data, ensure_ascii=False))


def get_pending_platforms():
    data = _redis_cmd("GET", "pending_platforms")
    return json.loads(data) if data else None


def clear_pending_platforms():
    _redis_cmd("DEL", "pending_platforms")


# --- Scored articles cache (for article selection flow) ---

def set_scored_articles(articles: list):
    _redis_cmd("SET", "scored_articles", json.dumps(articles, ensure_ascii=False))
    _redis_cmd("EXPIRE", "scored_articles", 3600)  # 1 hour TTL


def get_scored_articles():
    data = _redis_cmd("GET", "scored_articles")
    return json.loads(data) if data else None


def clear_scored_articles():
    _redis_cmd("DEL", "scored_articles")


# --- Content Bank ---

def save_to_content_bank(entry: dict):
    """Save published content to content bank for history."""
    import time
    entry["published_at"] = int(time.time())
    key = f"content_bank:{entry['published_at']}"
    _redis_cmd("SET", key, json.dumps(entry, ensure_ascii=False))
    _redis_cmd("LPUSH", "content_bank_index", key)
    # Keep last 100 entries
    _redis_cmd("LTRIM", "content_bank_index", 0, 99)


def get_content_bank(count: int = 10) -> list:
    """Get recent content bank entries."""
    keys = _redis_cmd("LRANGE", "content_bank_index", 0, count - 1)
    if not keys:
        return []
    entries = []
    for key in keys:
        data = _redis_cmd("GET", key)
        if data:
            entries.append(json.loads(data))
    return entries

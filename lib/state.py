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

"""Make.com webhook triggers for multi-platform publishing."""
import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

MAKE_WEBHOOK_POST = os.environ.get("MAKE_WEBHOOK_POST", "")
MAKE_WEBHOOK_COMMENT = os.environ.get("MAKE_WEBHOOK_COMMENT", "")
MAKE_WEBHOOK_TELEGRAM_CHANNEL = os.environ.get("MAKE_WEBHOOK_TELEGRAM_CHANNEL", "")
MAKE_WEBHOOK_INSTAGRAM = os.environ.get("MAKE_WEBHOOK_INSTAGRAM", "")

FB_PAGE_URL = os.environ.get("FB_PAGE_URL", "")
FB_GROUPS = [g.strip() for g in os.environ.get("FB_GROUPS", "").split(",") if g.strip()]
TELEGRAM_CHANNEL_ID = os.environ.get("TELEGRAM_CHANNEL_ID", "")


async def _trigger_webhook(webhook_url: str, payload: dict, label: str) -> bool:
    if not webhook_url:
        logger.warning(f"{label} webhook not configured — skipping")
        return False
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(webhook_url, json=payload)
        logger.info(f"Make.com {label}: {resp.status_code}")
        return resp.status_code == 200


async def trigger_post_to_facebook(content: str, image_url: str = None):
    return await _trigger_webhook(MAKE_WEBHOOK_POST, {
        "content": content,
        "page_url": FB_PAGE_URL,
        "groups": FB_GROUPS,
        "image_url": image_url,
    }, "facebook_post")


async def trigger_post_to_telegram_channel(content: str):
    return await _trigger_webhook(MAKE_WEBHOOK_TELEGRAM_CHANNEL, {
        "content": content,
        "channel_id": TELEGRAM_CHANNEL_ID,
    }, "telegram_channel")


async def trigger_post_to_instagram(caption: str, image_url: str = None):
    return await _trigger_webhook(MAKE_WEBHOOK_INSTAGRAM, {
        "caption": caption,
        "image_url": image_url,
    }, "instagram")


async def trigger_comment(post_url: str, comment_text: str):
    return await _trigger_webhook(MAKE_WEBHOOK_COMMENT, {
        "post_url": post_url,
        "comment": comment_text,
    }, "comment")


async def publish_to_platform(platform: str, content: str, image_url: str = None) -> bool:
    """Publish content to a specific platform."""
    if platform == "facebook":
        return await trigger_post_to_facebook(content, image_url)
    elif platform == "telegram":
        return await trigger_post_to_telegram_channel(content)
    elif platform == "instagram":
        return await trigger_post_to_instagram(content, image_url)
    else:
        logger.error(f"Unknown platform: {platform}")
        return False


async def publish_to_all(contents: dict, image_url: str = None) -> dict:
    """Publish to all platforms. contents = {"facebook": "...", "telegram": "...", "instagram": "..."}"""
    results = {}
    for platform, content in contents.items():
        if content:
            results[platform] = await publish_to_platform(platform, content, image_url)
    return results

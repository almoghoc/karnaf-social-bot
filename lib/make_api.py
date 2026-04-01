"""Make.com webhook trigger for Facebook publishing."""
import os
import json
import logging
import httpx

logger = logging.getLogger(__name__)

MAKE_WEBHOOK_POST = os.environ.get("MAKE_WEBHOOK_POST", "")
MAKE_WEBHOOK_COMMENT = os.environ.get("MAKE_WEBHOOK_COMMENT", "")

FB_PAGE_URL = os.environ.get("FB_PAGE_URL", "")
FB_GROUPS = [g.strip() for g in os.environ.get("FB_GROUPS", "").split(",") if g.strip()]


async def trigger_post_to_facebook(content: str, image_url: str = None):
    """Trigger Make.com scenario to publish post to page + groups."""
    if not MAKE_WEBHOOK_POST:
        logger.error("MAKE_WEBHOOK_POST not configured")
        return False

    payload = {
        "content": content,
        "page_url": FB_PAGE_URL,
        "groups": FB_GROUPS,
        "image_url": image_url,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(MAKE_WEBHOOK_POST, json=payload)
        logger.info(f"Make.com post trigger: {resp.status_code}")
        return resp.status_code == 200


async def trigger_comment(post_url: str, comment_text: str):
    """Trigger Make.com scenario to comment on a post."""
    if not MAKE_WEBHOOK_COMMENT:
        logger.error("MAKE_WEBHOOK_COMMENT not configured")
        return False

    payload = {
        "post_url": post_url,
        "comment": comment_text,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(MAKE_WEBHOOK_COMMENT, json=payload)
        logger.info(f"Make.com comment trigger: {resp.status_code}")
        return resp.status_code == 200

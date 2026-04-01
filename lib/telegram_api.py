"""Telegram Bot API wrapper for serverless (no python-telegram-bot dependency)."""
import json
import os
import httpx

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "")


async def _call(method: str, **kwargs):
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(f"{BASE_URL}/{method}", json=kwargs)
        return resp.json()


async def send_message(chat_id, text, reply_markup=None, parse_mode="Markdown",
                       disable_web_page_preview=True):
    params = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }
    if reply_markup:
        params["reply_markup"] = reply_markup
    return await _call("sendMessage", **params)


async def send_photo(chat_id, photo_url, caption=None):
    params = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        params["caption"] = caption
    return await _call("sendPhoto", **params)


async def answer_callback_query(callback_query_id, text=None):
    params = {"callback_query_id": callback_query_id}
    if text:
        params["text"] = text
    return await _call("answerCallbackQuery", **params)


async def edit_message_text(chat_id, message_id, text, parse_mode="Markdown"):
    return await _call("editMessageText",
                       chat_id=chat_id, message_id=message_id,
                       text=text, parse_mode=parse_mode)


def notify_sync(text):
    """Synchronous notification — for use in non-async contexts."""
    import httpx as hx
    hx.post(f"{BASE_URL}/sendMessage", json={
        "chat_id": MY_CHAT_ID, "text": text, "parse_mode": "Markdown",
    })

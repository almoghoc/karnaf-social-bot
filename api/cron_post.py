"""Vercel Cron: Auto post job — runs every 48 hours."""
import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.news import fetch_latest_news, pick_hottest
from lib.engine import generate_content
from lib.state import is_article_processed, set_pending_post
from lib.keyboards import auto_post_keyboard
from lib.telegram_api import send_message

MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "")


async def _run_auto_post():
    articles = fetch_latest_news()
    articles = [a for a in articles if not is_article_processed(a["link"])]

    if not articles:
        return {"status": "no_articles"}

    hottest = pick_hottest(articles)
    if not hottest:
        return {"status": "no_hottest"}

    # Generate post
    draft = generate_content(
        f"כותרת: {hottest['title']}\nתקציר: {hottest['summary']}\nמקור: {hottest['source']}",
        context_type="auto_post",
    )
    full_post = f"{draft.rstrip()}\n\n🔗 {hottest['link']}"

    # Save pending post
    set_pending_post({
        "draft": full_post,
        "article": hottest,
    })

    # Send to Telegram
    msg = (
        f"📰 *{hottest['title']}*\n"
        f"_{hottest['source']}_ | {hottest['link']}\n\n"
        f"━━━━━━━━━━━━━━━\n"
        f"📝 *הפוסט המוכן לפרסום:*\n\n"
        f"{full_post}\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"👆 לחץ *אשר* לפרסום בדף + קבוצות"
    )

    await send_message(
        MY_CHAT_ID, msg,
        reply_markup=auto_post_keyboard(),
        disable_web_page_preview=True,
    )

    return {"status": "sent", "title": hottest["title"]}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # Verify cron secret
        auth = self.headers.get("Authorization", "")
        cron_secret = os.environ.get("CRON_SECRET", "")
        if cron_secret and auth != f"Bearer {cron_secret}":
            self.send_response(401)
            self.end_headers()
            return

        try:
            result = asyncio.run(_run_auto_post())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

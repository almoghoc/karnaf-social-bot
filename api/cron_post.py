"""Vercel Cron: Auto post job — runs every 48 hours.
Scans all sources, scores articles, sends top 3 to Telegram for selection."""
import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.news import fetch_latest_news, pick_top_articles
from lib.state import is_article_processed, set_scored_articles
from lib.keyboards import article_select_keyboard
from lib.telegram_api import send_message

MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "")


async def _run_auto_post():
    articles = fetch_latest_news()
    articles = [a for a in articles if not is_article_processed(a["link"])]

    if not articles:
        return {"status": "no_articles"}

    top = pick_top_articles(articles, count=3)
    if not top:
        return {"status": "no_scored"}

    set_scored_articles(top)

    # Build BLUF summary
    lines = "🦏 *סריקה אוטומטית — Top 3:*\n\n"
    for i, a in enumerate(top):
        score = a.get("score", {})
        medal = "🥇🥈🥉"[i] if i < 3 else "📰"
        lines += (
            f"{medal} *{a['title']}*\n"
            f"_{a['source']}_\n"
            f"💡 {score.get('why', '')}\n"
            f"📊 ציון: *{score.get('total', '?')}* "
            f"(מחלוקת:{score.get('controversy', '?')} "
            f"תועלת:{score.get('financial_utility', '?')} "
            f"הוכחה:{score.get('social_proof', '?')} "
            f"דחיפות:{score.get('urgency', '?')})\n\n"
        )

    lines += "👆 בחר כתבה לייצור תוכן"

    await send_message(
        MY_CHAT_ID, lines,
        reply_markup=article_select_keyboard(top),
        disable_web_page_preview=True,
    )

    return {"status": "sent", "count": len(top), "titles": [a["title"] for a in top]}


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
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

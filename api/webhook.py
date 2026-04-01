"""Vercel serverless: Telegram webhook handler."""
import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.telegram_api import send_message, answer_callback_query, edit_message_text
from lib.keyboards import auto_post_keyboard, comment_keyboard, approval_keyboard
from lib.engine import generate_content
from lib.state import (
    get_pending_post, clear_pending_post, mark_article_processed,
    get_pending_comment, clear_pending_comment, mark_post_commented,
)
from lib.make_api import trigger_post_to_facebook, trigger_comment
from lib.news import fetch_latest_news, pick_hottest

MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "")


async def handle_callback(callback_query):
    data = callback_query.get("data", "")
    cb_id = callback_query.get("id")
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]

    if data == "auto_approve":
        pending = get_pending_post()
        if not pending:
            await answer_callback_query(cb_id, "אין פוסט ממתין")
            return
        await answer_callback_query(cb_id, "מפרסם...")
        await edit_message_text(chat_id, msg_id, "⏳ מפרסם בדף + קבוצות...")
        success = await trigger_post_to_facebook(pending["draft"])
        if success:
            mark_article_processed(pending["article"]["link"])
            clear_pending_post()
            await edit_message_text(chat_id, msg_id, "✅ פורסם בהצלחה בדף + קבוצות!")
        else:
            await edit_message_text(chat_id, msg_id, "❌ שגיאה בפרסום — בדוק Make.com")

    elif data == "auto_reject":
        clear_pending_post()
        await answer_callback_query(cb_id, "נדחה")
        await edit_message_text(chat_id, msg_id, "❌ הפוסט נדחה")

    elif data == "auto_edit":
        await answer_callback_query(cb_id, "שלח את הטקסט המעודכן")
        await send_message(chat_id, "✏️ שלח את הטקסט המעודכן לפוסט:")

    elif data == "comment_approve":
        pending = get_pending_comment()
        if not pending:
            await answer_callback_query(cb_id, "אין תגובה ממתינה")
            return
        await answer_callback_query(cb_id, "מפרסם תגובה...")
        await edit_message_text(chat_id, msg_id, "⏳ מפרסם תגובה...")
        success = await trigger_comment(pending["post"]["url"], pending["draft"])
        if success:
            mark_post_commented(pending["post"]["url"])
            clear_pending_comment()
            await edit_message_text(chat_id, msg_id, "✅ תגובה פורסמה!")
        else:
            await edit_message_text(chat_id, msg_id, "❌ שגיאה — בדוק Make.com")

    elif data == "comment_reject":
        clear_pending_comment()
        await answer_callback_query(cb_id, "נדחה")
        await edit_message_text(chat_id, msg_id, "❌ התגובה נדחתה")


async def handle_command(message):
    text = message.get("text", "")
    chat_id = message["chat"]["id"]

    if text == "/start":
        await send_message(chat_id,
            "🦏 *קרנף נדל\"ן — בוט תוכן*\n\n"
            "/scan — סריקת חדשות נדל\"ן\n"
            "/status — סטטוס הבוט\n\n"
            "שלח טקסט ואייצר ממנו פוסט מקצועי."
        )

    elif text == "/scan":
        await send_message(chat_id, "🔍 סורק חדשות נדל\"ן מ-5 מקורות...")
        articles = fetch_latest_news()
        if not articles:
            await send_message(chat_id, "לא נמצאו כתבות נדל\"ן. נסה שוב מאוחר יותר.")
            return

        lines = "📰 *חדשות נדל\"ן חמות:*\n\n"
        for i, a in enumerate(articles, 1):
            lines += f"*{i}.* {a['title']}\n_{a['source']}_\n{a['link']}\n\n"
        await send_message(chat_id, lines, disable_web_page_preview=True)

        hottest = pick_hottest(articles)
        if not hottest:
            return
        await send_message(chat_id, f"🔥 הכתבה הכי חמה: *{hottest['title']}*\nמייצר פוסט...")

        draft = generate_content(
            f"כותרת: {hottest['title']}\nתקציר: {hottest['summary']}\nמקור: {hottest['source']}",
            context_type="auto_post",
        )
        full_post = f"{draft.rstrip()}\n\n🔗 {hottest['link']}"

        from lib.state import set_pending_post
        set_pending_post({"draft": full_post, "article": hottest})

        await send_message(
            chat_id,
            f"━━━━━━━━━━━━━━━\n📝 *הפוסט המוכן לפרסום:*\n\n{full_post}\n━━━━━━━━━━━━━━━",
            reply_markup=auto_post_keyboard(),
            disable_web_page_preview=True,
        )

    elif text == "/status":
        await send_message(chat_id,
            "🦏 *סטטוס קרנף נדל\"ן*\n\n"
            "✅ הבוט פעיל על Vercel\n"
            "⏰ פוסט אוטומטי: כל 48 שעות\n"
            "💬 תגובה ויראלית: כל 24 שעות\n"
            "📡 פרסום: דרך Make.com"
        )

    else:
        # Free text — generate post
        draft = generate_content(text, context_type="post")
        from lib.state import set_pending_post
        set_pending_post({"draft": draft, "article": {"link": "", "title": text[:50]}})
        await send_message(
            chat_id,
            f"━━━━━━━━━━━━━━━\n📝 *הפוסט:*\n\n{draft}\n━━━━━━━━━━━━━━━",
            reply_markup=auto_post_keyboard(),
        )


async def process_update(update):
    if "callback_query" in update:
        await handle_callback(update["callback_query"])
    elif "message" in update:
        await handle_command(update["message"])


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        update = json.loads(body)

        try:
            asyncio.run(process_update(update))
        except Exception as e:
            print(f"Error processing update: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Karnaf Bot Webhook Active")

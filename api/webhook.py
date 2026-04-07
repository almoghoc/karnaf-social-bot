"""Vercel serverless: Telegram webhook handler."""
import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.telegram_api import send_message, answer_callback_query, edit_message_text
from lib.keyboards import (
    auto_post_keyboard, comment_keyboard, approval_keyboard,
    multiplatform_keyboard, platform_approve_keyboard, approve_all_keyboard,
    article_select_keyboard,
)
from lib.engine import generate_content, generate_all_platforms
from lib.state import (
    get_pending_post, set_pending_post, clear_pending_post, mark_article_processed,
    get_pending_comment, clear_pending_comment, mark_post_commented,
    set_pending_platforms, get_pending_platforms, clear_pending_platforms,
    set_scored_articles, get_scored_articles, clear_scored_articles,
    save_to_content_bank, get_content_bank,
)
from lib.make_api import (
    trigger_post_to_facebook, trigger_comment,
    publish_to_platform, publish_to_all,
)
from lib.news import fetch_latest_news, pick_hottest, pick_top_articles

MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "")

PLATFORM_EMOJI = {"facebook": "📘", "telegram": "✈️", "instagram": "📸"}


async def handle_callback(callback_query):
    data = callback_query.get("data", "")
    cb_id = callback_query.get("id")
    chat_id = callback_query["message"]["chat"]["id"]
    msg_id = callback_query["message"]["message_id"]

    # --- Legacy: single-platform auto approve ---
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
            save_to_content_bank({
                "article": pending["article"],
                "content": {"facebook": pending["draft"]},
                "platforms": ["facebook"],
            })
            clear_pending_post()
            await edit_message_text(chat_id, msg_id, "✅ פורסם בהצלחה בדף + קבוצות!")
        else:
            await edit_message_text(chat_id, msg_id, "❌ שגיאה בפרסום — בדוק Make.com")

    elif data == "auto_reject":
        clear_pending_post()
        clear_pending_platforms()
        clear_scored_articles()
        await answer_callback_query(cb_id, "נדחה")
        await edit_message_text(chat_id, msg_id, "❌ נדחה")

    elif data == "auto_edit":
        await answer_callback_query(cb_id, "שלח את הטקסט המעודכן")
        await send_message(chat_id, "✏️ שלח את הטקסט המעודכן לפוסט:")

    # --- Article selection from scored list ---
    elif data.startswith("select_article_"):
        idx = int(data.split("_")[-1])
        articles = get_scored_articles()
        if not articles or idx >= len(articles):
            await answer_callback_query(cb_id, "כתבה לא נמצאה")
            return
        article = articles[idx]
        await answer_callback_query(cb_id, "נבחרה!")
        set_pending_post({"draft": "", "article": article})
        await edit_message_text(chat_id, msg_id,
            f"🔥 נבחר: *{article['title']}*\n"
            f"📊 ציון: {article['score']['total']} | {article['score'].get('why', '')}\n\n"
            f"בחר איך לייצר:",
            reply_markup=multiplatform_keyboard(),
        )

    # --- Generate content for platforms ---
    elif data.startswith("generate_"):
        pending = get_pending_post()
        if not pending or not pending.get("article"):
            await answer_callback_query(cb_id, "אין כתבה נבחרת")
            return

        article = pending["article"]
        raw = f"כותרת: {article['title']}\nתקציר: {article.get('summary', '')}\nמקור: {article['source']}"
        target = data.replace("generate_", "")

        await answer_callback_query(cb_id, "מייצר תוכן...")
        await edit_message_text(chat_id, msg_id, "⏳ מייצר תוכן...")

        if target == "all":
            contents = generate_all_platforms(raw)
        elif target in ("facebook", "telegram", "instagram"):
            ctx = {"facebook": "facebook_post", "telegram": "telegram_post", "instagram": "instagram_caption"}
            contents = {target: generate_content(raw, ctx[target])}
        else:
            await edit_message_text(chat_id, msg_id, "❌ פלטפורמה לא מוכרת")
            return

        # Add link to facebook content
        if "facebook" in contents and article.get("link"):
            contents["facebook"] = f"{contents['facebook'].rstrip()}\n\n🔗 {article['link']}"
        if "telegram" in contents and article.get("link"):
            contents["telegram"] = f"{contents['telegram'].rstrip()}\n\n🔗 {article['link']}"

        set_pending_platforms({"contents": contents, "article": article})

        # Show all generated content
        msg_parts = []
        for platform, content in contents.items():
            emoji = PLATFORM_EMOJI.get(platform, "📝")
            msg_parts.append(f"{emoji} *{platform.upper()}:*\n\n{content}")

        full_msg = "\n\n━━━━━━━━━━━━━━━\n\n".join(msg_parts)
        await send_message(chat_id,
            f"━━━━━━━━━━━━━━━\n{full_msg}\n━━━━━━━━━━━━━━━",
            reply_markup=approve_all_keyboard(),
            disable_web_page_preview=True,
        )

    # --- Publish to specific platform or all ---
    elif data.startswith("publish_"):
        target = data.replace("publish_", "")
        pending = get_pending_platforms()
        if not pending:
            await answer_callback_query(cb_id, "אין תוכן ממתין")
            return

        contents = pending["contents"]
        article = pending["article"]
        await answer_callback_query(cb_id, "מפרסם...")

        if target == "all":
            await edit_message_text(chat_id, msg_id, "⏳ מפרסם בכל הפלטפורמות...")
            results = await publish_to_all(contents)
            succeeded = [p for p, ok in results.items() if ok]
            failed = [p for p, ok in results.items() if not ok]
        else:
            await edit_message_text(chat_id, msg_id, f"⏳ מפרסם ב-{target}...")
            ok = await publish_to_platform(target, contents.get(target, ""))
            succeeded = [target] if ok else []
            failed = [target] if not ok else []

        if article.get("link"):
            mark_article_processed(article["link"])
        if succeeded:
            save_to_content_bank({
                "article": article,
                "content": {p: contents.get(p, "") for p in succeeded},
                "platforms": succeeded,
            })

        status_parts = []
        for p in succeeded:
            status_parts.append(f"✅ {PLATFORM_EMOJI.get(p, '')} {p}")
        for p in failed:
            status_parts.append(f"❌ {PLATFORM_EMOJI.get(p, '')} {p}")

        clear_pending_platforms()
        clear_pending_post()
        await edit_message_text(chat_id, msg_id, "\n".join(status_parts) or "✅ בוצע")

    elif data.startswith("reject_"):
        clear_pending_platforms()
        await answer_callback_query(cb_id, "נדחה")
        await edit_message_text(chat_id, msg_id, "❌ נדחה")

    elif data.startswith("edit_"):
        await answer_callback_query(cb_id, "שלח את הטקסט המעודכן")
        platform = data.replace("edit_", "")
        await send_message(chat_id, f"✏️ שלח את הטקסט המעודכן ל-{platform}:")

    # --- Legacy approval keyboard ---
    elif data == "approve":
        pending = get_pending_post()
        if not pending:
            await answer_callback_query(cb_id, "אין פוסט ממתין")
            return
        await answer_callback_query(cb_id, "מפרסם...")
        await edit_message_text(chat_id, msg_id, "⏳ מפרסם...")
        success = await trigger_post_to_facebook(pending["draft"])
        if success:
            mark_article_processed(pending["article"]["link"])
            clear_pending_post()
            await edit_message_text(chat_id, msg_id, "✅ פורסם!")
        else:
            await edit_message_text(chat_id, msg_id, "❌ שגיאה — בדוק Make.com")

    elif data == "reject":
        clear_pending_post()
        await answer_callback_query(cb_id, "נדחה")
        await edit_message_text(chat_id, msg_id, "❌ נדחה")

    elif data == "edit":
        await answer_callback_query(cb_id, "שלח את הטקסט המעודכן")
        await send_message(chat_id, "✏️ שלח את הטקסט המעודכן:")

    # --- Comments ---
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

    elif data == "comment_edit":
        await answer_callback_query(cb_id, "שלח את התגובה המעודכנת")
        await send_message(chat_id, "✏️ שלח את התגובה המעודכנת:")

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
            "/scan — סריקת חדשות + דירוג (Top 3)\n"
            "/history — היסטוריית פרסומים\n"
            "/status — סטטוס הבוט\n\n"
            "שלח טקסט ואייצר ממנו פוסט מקצועי."
        )

    elif text == "/scan":
        from lib.news import RSS_FEEDS, HTML_SOURCES
        total_sources = len(RSS_FEEDS) + len(HTML_SOURCES)
        await send_message(chat_id, f"🔍 סורק חדשות נדל\"ן מ-{total_sources} מקורות...")
        articles = fetch_latest_news()
        if not articles:
            await send_message(chat_id, "לא נמצאו כתבות נדל\"ן. נסה שוב מאוחר יותר.")
            return

        # Score and pick top 3
        top = pick_top_articles(articles, count=3)
        if not top:
            await send_message(chat_id, "לא הצלחתי לדרג את הכתבות. נסה שוב.")
            return

        # Cache scored articles for selection
        set_scored_articles(top)

        # Build BLUF summary for each
        lines = "📰 *Top 3 — כתבות חמות:*\n\n"
        for i, a in enumerate(top):
            score = a.get("score", {})
            medal = "🥇🥈🥉"[i] if i < 3 else "📰"
            lines += (
                f"{medal} *{a['title']}*\n"
                f"_{a['source']}_ | ציון: *{score.get('total', '?')}*\n"
                f"📊 מחלוקת:{score.get('controversy', '?')} | "
                f"תועלת:{score.get('financial_utility', '?')} | "
                f"הוכחה:{score.get('social_proof', '?')} | "
                f"דחיפות:{score.get('urgency', '?')}\n"
                f"💡 {score.get('why', '')}\n\n"
            )

        await send_message(chat_id, lines,
            reply_markup=article_select_keyboard(top),
            disable_web_page_preview=True,
        )

    elif text == "/history":
        entries = get_content_bank(5)
        if not entries:
            await send_message(chat_id, "📭 אין היסטוריית פרסומים עדיין.")
            return
        lines = "📚 *פרסומים אחרונים:*\n\n"
        for e in entries:
            article = e.get("article", {})
            platforms = ", ".join(e.get("platforms", []))
            lines += f"• *{article.get('title', '?')[:50]}*\n  {platforms}\n\n"
        await send_message(chat_id, lines)

    elif text == "/status":
        from lib.news import RSS_FEEDS, HTML_SOURCES
        total_sources = len(RSS_FEEDS) + len(HTML_SOURCES)
        await send_message(chat_id,
            "🦏 *סטטוס קרנף נדל\"ן*\n\n"
            f"✅ הבוט פעיל על Vercel\n"
            f"📡 {total_sources} מקורות חדשות\n"
            "⏰ סריקה אוטומטית: כל 48 שעות\n"
            "🌐 פלטפורמות: Facebook, Telegram, Instagram\n"
            "📡 פרסום: דרך Make.com"
        )

    else:
        # Free text — generate post with platform selection
        set_pending_post({"draft": "", "article": {"link": "", "title": text[:50], "source": "user", "summary": text}})
        await send_message(chat_id,
            "✍️ קיבלתי. בחר פלטפורמה:",
            reply_markup=multiplatform_keyboard(),
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

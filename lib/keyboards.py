"""Telegram inline keyboard builders — raw JSON format for serverless."""


def auto_post_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✅ אשר — פרסם בדף + קבוצות", "callback_data": "auto_approve"}],
            [
                {"text": "✏️ ערוך", "callback_data": "auto_edit"},
                {"text": "❌ דחה", "callback_data": "auto_reject"},
            ],
        ]
    }


def multiplatform_keyboard():
    """After article selection — generate for all platforms."""
    return {
        "inline_keyboard": [
            [{"text": "🌐 ייצר לכל הפלטפורמות", "callback_data": "generate_all"}],
            [{"text": "📘 פייסבוק בלבד", "callback_data": "generate_facebook"}],
            [{"text": "✈️ טלגרם בלבד", "callback_data": "generate_telegram"}],
            [{"text": "📸 אינסטגרם בלבד", "callback_data": "generate_instagram"}],
            [{"text": "❌ דחה", "callback_data": "auto_reject"}],
        ]
    }


def platform_approve_keyboard(platform: str):
    """Approve/reject a specific platform post."""
    return {
        "inline_keyboard": [
            [{"text": f"✅ אשר — פרסם", "callback_data": f"publish_{platform}"}],
            [
                {"text": "✏️ ערוך", "callback_data": f"edit_{platform}"},
                {"text": "❌ דחה", "callback_data": f"reject_{platform}"},
            ],
        ]
    }


def approve_all_keyboard():
    """Approve all platforms at once."""
    return {
        "inline_keyboard": [
            [{"text": "✅ אשר הכל — פרסם בכל הפלטפורמות", "callback_data": "publish_all"}],
            [
                {"text": "📘 פייסבוק", "callback_data": "publish_facebook"},
                {"text": "✈️ טלגרם", "callback_data": "publish_telegram"},
                {"text": "📸 אינסטגרם", "callback_data": "publish_instagram"},
            ],
            [{"text": "❌ דחה הכל", "callback_data": "auto_reject"}],
        ]
    }


def article_select_keyboard(articles: list):
    """Let user pick which article to generate content for."""
    buttons = []
    for i, a in enumerate(articles):
        score = a.get("score", {}).get("total", 0)
        buttons.append([{"text": f"{'🥇🥈🥉'[i] if i < 3 else '📰'} [{score}] {a['title'][:40]}...", "callback_data": f"select_article_{i}"}])
    buttons.append([{"text": "❌ סגור", "callback_data": "auto_reject"}])
    return {"inline_keyboard": buttons}


def comment_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✅ אשר — פרסם תגובה", "callback_data": "comment_approve"}],
            [
                {"text": "✏️ ערוך", "callback_data": "comment_edit"},
                {"text": "❌ דחה", "callback_data": "comment_reject"},
            ],
        ]
    }


def approval_keyboard():
    return {
        "inline_keyboard": [
            [{"text": "✅ אשר", "callback_data": "approve"}],
            [
                {"text": "✏️ ערוך", "callback_data": "edit"},
                {"text": "❌ דחה", "callback_data": "reject"},
            ],
        ]
    }

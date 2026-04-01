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

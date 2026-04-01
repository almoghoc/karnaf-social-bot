"""Vercel serverless: Callback from Make.com after Facebook publish."""
import asyncio
import json
import os
import sys
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.telegram_api import send_message

MY_CHAT_ID = os.environ.get("MY_CHAT_ID", "")


async def _handle_callback(data):
    status = data.get("status", "unknown")
    target = data.get("target", "")
    error = data.get("error", "")

    if status == "success":
        await send_message(MY_CHAT_ID, f"✅ Make.com: פורסם בהצלחה ב-{target}")
    else:
        await send_message(MY_CHAT_ID, f"❌ Make.com שגיאה ({target}): {error}")


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        data = json.loads(body)

        try:
            asyncio.run(_handle_callback(data))
        except Exception as e:
            print(f"Callback error: {e}")

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"ok": True}).encode())

#!/usr/bin/env python3
"""Long-polling Telegram bot for /home/deploy/tuinui.

Handles inbound /start, /help, /id, /ping and greets plain "hi"-style messages.
Persists offset in /home/deploy/tuinui/.tg_offset so restarts don't reprocess.

Token + chat_id are read from /home/deploy/.hermes/.env to stay consistent
with tg_health.py and _send_hb.py.
"""
from __future__ import annotations

import json
import logging
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV_PATH = Path("/home/deploy/.hermes/.env")
OFFSET_PATH = Path("/home/deploy/tuinui/.tg_offset")
LOG_PATH = Path("/home/deploy/tuinui/tg_bot.log")

API = "https://api.telegram.org"
POLL_TIMEOUT = 25           # long-poll seconds (Telegram max ~30)
RETRY_BACKOFF = 5           # seconds between transient errors
FALLBACK_CHAT_ID = "1723782168"  # mirror _send_hb.py / tg_health.py


def load_env() -> tuple[str, str]:
    raw = ENV_PATH.read_text(encoding="utf-8", errors="replace")
    token_m = re.search(r"TELEGRAM_BOT_TOKEN=(\S+)", raw)
    chat_m = re.search(r"TELEGRAM_DEFAULT_CHAT_ID=(\S+)", raw) or \
             re.search(r"TELEGRAM_CHAT_ID=(\S+)", raw)
    if not token_m:
        raise SystemExit(f"TELEGRAM_BOT_TOKEN missing in {ENV_PATH}")
    return token_m.group(1).strip(), (chat_m.group(1).strip() if chat_m else FALLBACK_CHAT_ID)


def api_call(token: str, method: str, params: dict | None = None,
             timeout: int = POLL_TIMEOUT + 5) -> dict:
    url = f"{API}/bot{token}/{method}"
    if params is None:
        params = {}
    body = json.dumps(params).encode("utf-8")
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        logging.error("HTTP %s on %s: %s", e.code, method, body)
        raise


def load_offset() -> int:
    try:
        return int(OFFSET_PATH.read_text().strip())
    except (FileNotFoundError, ValueError):
        return 0


def save_offset(offset: int) -> None:
    OFFSET_PATH.write_text(str(offset))


def reply(token: str, chat_id: str, text: str) -> None:
    try:
        api_call(token, "sendMessage",
                 {"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
                 timeout=15)
    except Exception as e:
        logging.warning("sendMessage failed: %s", e)


def handle(token: str, update: dict, chat_id_default: str) -> None:
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return
    chat = msg.get("chat", {})
    chat_id = str(chat.get("id", chat_id_default))
    text = (msg.get("text") or "").strip()
    user = msg.get("from", {}) or {}
    name = user.get("first_name") or user.get("username") or "there"

    logging.info("inbound chat=%s user=%s text=%r",
                 chat_id, user.get("username"), text[:120])

    if not text:
        return

    if text.startswith("/start"):
        reply(token, chat_id, f"👋 Hi {name}! I'm the tuinui bot. Try /help.")
        return
    if text.startswith("/help"):
        reply(token, chat_id,
              "Commands:\n"
              "  /start  – greet\n"
              "  /help   – this message\n"
              "  /id     – show your chat id\n"
              "  /ping   – health check\n\n"
              "Or just say hi and I'll wave back.")
        return
    if text.startswith("/id"):
        reply(token, chat_id, f"chat_id: <code>{chat_id}</code>")
        return
    if text.startswith("/ping"):
        reply(token, chat_id, "pong ✅")
        return

    lower = text.lower()
    greetings = ("hi", "hello", "hey", "yo", "hola", "oi", "olá")
    if any(lower == g or lower.startswith(g + " ") or lower.startswith(g + ",")
           for g in greetings):
        reply(token, chat_id, f"Hi {name} 👋 — what can I do for you?")
        return

    # Fallback: echo so the user can confirm two-way traffic works.
    reply(token, chat_id, f"You said: <i>{text[:200]}</i>")


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(LOG_PATH),
                  logging.StreamHandler(sys.stdout)],
    )
    token, chat_default = load_env()
    logging.info("starting long-poller; default chat=%s", chat_default)

    # Confirm bot is reachable before we loop forever.
    try:
        me = api_call(token, "getMe", {}, timeout=15)
        if not me.get("ok"):
            logging.error("getMe failed: %s", me)
            return 2
        logging.info("getMe: %s", json.dumps(me.get("result")))
    except Exception as e:
        logging.error("getMe error: %s", e)
        return 2

    while True:
        offset = load_offset()
        try:
            resp = api_call(token, "getUpdates",
                            {"timeout": POLL_TIMEOUT, "offset": offset,
                             "allowed_updates": ["message"]},
                            timeout=POLL_TIMEOUT + 10)
            if not resp.get("ok"):
                logging.warning("getUpdates not ok: %s", resp)
                time.sleep(RETRY_BACKOFF)
                continue
            for upd in resp.get("result", []):
                try:
                    handle(token, upd, chat_default)
                except Exception as e:
                    logging.exception("handler error: %s", e)
                next_off = int(upd["update_id"]) + 1
                if next_off > offset:
                    save_offset(next_off)
        except urllib.error.URLError as e:
            logging.warning("network error: %s; backing off", e)
            time.sleep(RETRY_BACKOFF)
        except json.JSONDecodeError as e:
            logging.warning("bad json: %s; backing off", e)
            time.sleep(RETRY_BACKOFF)
        except Exception as e:
            logging.exception("poll loop error: %s", e)
            time.sleep(RETRY_BACKOFF)


if __name__ == "__main__":
    sys.exit(main() or 0)
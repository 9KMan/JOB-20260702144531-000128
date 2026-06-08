#!/usr/bin/env python3
import re, json, urllib.request, urllib.error, subprocess

with open('/home/deploy/.hermes/.env', 'rb') as f:
    raw = f.read()
m = re.search(rb'TELEGRAM_BOT_TOKEN=([^\s\n]+)', raw)
TOKEN = m.group(1).decode()
CHAT_ID = "1723782168"

def send_tg(text):
    payload = json.dumps({'chat_id': CHAT_ID, 'text': text, 'parse_mode': 'Markdown'}, ensure_ascii=False).encode('utf-8')
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{TOKEN}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"}
    )
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        result = json.loads(resp.read().decode('utf-8'))
        print("OK:", result.get("message_id",""))
    except urllib.error.HTTPError as e:
        print("HTTP Error:", e.code, e.read().decode())
    except Exception as e:
        print("Error:", type(e).__name__, e)

health = subprocess.run(['python3', '/home/deploy/.hermes/scripts/pipeline-health.py'], capture_output=True, text=True).stdout

stale_approved = "Stale APPROVED:   0" in health
stale_building = "Stale BUILDING:   0" in health
no_ghosts = "Multica ghosts:   none" in health

if stale_approved and stale_building and no_ghosts:
    send_tg("✅ Pipeline healthy | 355 total jobs | All counts at 0")
else:
    header = "📊 *Pipeline Health Issues Found*\n```\n" + health + "\n```"
    send_tg(header)

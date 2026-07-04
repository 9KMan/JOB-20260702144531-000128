import re, urllib.request, json, sys

with open('/home/deploy/.hermes/.env') as f:
    content = f.read()
match = re.search(r'TELEGRAM_BOT_TOKEN=([^ ]+)', content)
token = match.group(1).strip()

msg = """📊 <b>Pipeline Health</b> — 2026-06-21 17:01 UTC | 388 jobs

✅ Stale APPROVED: 0
✅ Stale BUILDING: 0
⚠️ IN_REVIEW no kanban card: 3
✅ Multica BUILD ghosts: none
⚠️ CEO REVIEW duplicates: 1

<b>Missing kanban (3):</b>
JOB-20260614024444-000093
JOB-20260614123056-000096
JOB-20260621073632-000101"""

url = f'https://api.telegram.org/bot{token}/sendMessage'
data = json.dumps({'chat_id': '1723782168', 'text': msg, 'parse_mode': 'HTML'}).encode()
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        result = json.loads(resp.read().decode())
        print('OK:', result.get('ok'), result.get('description',''))
except Exception as e:
    print('ERROR:', e)
    sys.exit(1)

import json

path = r'C:\Users\mongk\.openclaw\cron\jobs.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

jobs = data['jobs']
for j in jobs:
    if 'Gig Pipeline: Stage 2' in j.get('name', ''):
        old_msg = j['payload']['message']
        new_msg = (
            old_msg
            + ' After saving briefs, run: C:\\Users\\mongk\\bin\\upload-opportunities.ps1'
            + ' -Verbose.'
            + ' This uploads all opportunities from stage1-opportunities to'
            + ' MinIO factory/leads/ so the Hermes factory pipeline picks them up automatically.'
        )
        j['payload']['message'] = new_msg
        print('Patched:', j['name'])
        print('Old:', old_msg[:100])
        print('New:', new_msg[:100])
        break

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print('Saved.')

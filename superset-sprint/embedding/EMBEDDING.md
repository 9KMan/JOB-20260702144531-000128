# Superset Embedded Analytics Guide

## Overview

Superset 4.0+ supports embedded analytics via:
1. **Embedded SDK** (JavaScript) — embed charts/dashboards in iframes
2. **Standalone mode** — full-page embedded dashboards
3. **Guest tokens** — JWT-based anonymous access

---

## Setup Steps

### 1. Enable Embedding Feature Flag

```yaml
# docker-compose.yml environment
FEATURE_FLAGS: '{"EMBEDDED_SUPERSET": true}'
```

Or via Superset UI: **Settings > Feature Flags > EMBEDDED_SUPERSET**

### 2. Configure Guest Token Auth

In `superset_config.py`:

```python
GUEST_TOKEN_JWT_SECRET = "your-secret-key-min-32-chars!!"
GUEST_TOKEN_JWT_ALGO = "HS256"

# Add to Extra JSON for the dashboard:
{
  "guest_token": {
    "user": {"username": "guest"},
    "roles": ["Gamma"],
    "resources": [{"type": "dashboard", "id": "123"}],
    "rls": [{"clause": "tenant_id = 'acme'"}]
  }
}
```

### 3. Create Embedded Dashboard

1. Create dashboard in Superset
2. Go to **Dashboard > Actions > Embed**
3. Copy the embed snippet

### 4. Embed Code Example

```html
<!-- Option A: iframe embed -->
<iframe
  src="http://localhost:8088/api/v1/embedded/dashboard/{dashboard_id}"
  width="100%"
  height="600"
  frameborder="0"
></iframe>

<!-- Option B: Embedded SDK (recommended) -->
<div id="my-dashboard" style="height: 600px;"></div>

<script type="module">
  import { createDashboardEmbed } from 'https://unpkg.com/@superset-ui/embedded-sdk';

  createDashboardEmbed({
    id: 'dashboard-id-here',
    supersetUrl: 'http://localhost:8088',
    getGuestToken: async () => {
      const resp = await fetch('/api/guest-token');
      return (await resp.json()).token;
    },
    mountPoint: document.getElementById('my-dashboard'),
    config: {
      uiConfig: {
        showTitle: true,
        showControls: true,
        hideTitle: false
      }
    }
  });
</script>
```

### 5. Guest Token API Endpoint (Backend)

```javascript
// Node.js example
const jwt = require('jsonwebtoken');
const SECRET = process.env.SUPERSET_GUEST_SECRET;

app.get('/api/guest-token', (req, res) => {
  const tenant = req.query.tenant; // e.g., 'acme'
  
  const token = jwt.sign(
    {
      user: { username: 'guest' },
      roles: ['Gamma'],
      resources: [{ type: 'dashboard', id: 'dashboard-uuid' }],
      rls: [{ clause: `tenant_id = '${tenant}'` }]
    },
    SECRET,
    { expiresIn: '1h' }
  );
  
  res.json({ token });
});
```

---

## Security Checklist

- [ ] Guest tokens have short expiry (1h max)
- [ ] RLS applied to all guest token queries
- [ ] iframe uses `sandbox` attribute with appropriate permissions
- [ ] Superset behind reverse proxy with HTTPS
- [ ] Secret key is strong and rotated

---

## iframe Embed with Nginx

```nginx
# nginx/embed.conf
location /embedded/ {
    proxy_pass http://superset-app:8088/api/v1/embedded/;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    # Prevent clickjacking
    add_header X-Frame-Options "SAMEORIGIN" always;
}
```

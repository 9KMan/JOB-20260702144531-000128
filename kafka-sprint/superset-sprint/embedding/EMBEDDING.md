# Superset Dashboard Embedding Guide

## Two Embedding Modes

### 1. Simple Iframe Embed (Superset >= 1.5)

```
http://superset-server:8088/superset/embedded/1/
```

Enable embedding on a dashboard:
1. Edit dashboard > Edit Properties
2. ✅ "Enable Embedding"
3. Copy the embed URL

### 2. Guest Token Embed (Recommended for SaaS)

For multi-tenant, use guest tokens — they pass through the RLS policies automatically.

```javascript
// Backend: Issue a guest token
const response = await fetch('http://superset-server:8088/api/v1/security/guest_token/', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': 'Bearer YOUR_API_KEY'
  },
  body: JSON.stringify({
    user: {
      username: 'bob@acme.com',
      roles: ['Manager_Acme']
    },
    resources: [{
      type: 'dashboard',
      id: '1'
    }],
    rls: [{
      clause: "company_id = 1 AND business_unit = 'Sales'"
    }]
  })
});

const { token } = await response.json();

// Frontend: Embed with token
const iframe = document.createElement('iframe');
iframe.src = 'http://superset-server:8088/superset/embedded/1/?token=' + token;
iframe.style.width = '100%';
iframe.style.height = '600px';
document.getElementById('dashboard-container').appendChild(iframe);
```

## nginx CSP Configuration

```nginx
server {
    listen 80;
    server_name your-saas.com;

    # Superset proxy
    location /superset/ {
        proxy_pass http://superset:8088/;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Content Security Policy for iframe embedding
        add_header Content-Security-Policy 
            "frame-ancestors 'self' https://your-saas.com https://app.your-saas.com;" 
            always;
        
        # Prevent clickjacking
        add_header X-Frame-Options "SAMEORIGIN" always;
    }
}
```

## Embedding HTML Example

```html
<!DOCTYPE html>
<html>
<head>
    <title>Customer Dashboard</title>
    <style>
        body { margin: 0; padding: 20px; font-family: sans-serif; }
        #dashboard { width: 100%; height: 700px; border: none; }
    </style>
</head>
<body>
    <h1>Sales Dashboard</h1>
    <div id="dashboard-container"></div>
    
    <script>
        // Fetch guest token from your backend
        async function loadDashboard() {
            const resp = await fetch('/api/superset-guest-token');
            const { token } = await resp.json();
            
            const iframe = document.createElement('iframe');
            iframe.id = 'dashboard';
            iframe.src = 'http://superset:8088/superset/embedded/1/?token=' + token;
            iframe.allow = 'fullscreen';
            document.getElementById('dashboard-container').appendChild(iframe);
        }
        loadDashboard();
    </script>
</body>
</html>
```

## Highcharts Plugin Setup

Superset >= 3.0 has native Highcharts support. For older versions:

```bash
# Install Highcharts plugin
pip install highcharts-superset

# In superset_config.py
from highcharts import HighchartsChartPlugin

def guest_token_func():
    # Custom guest token logic
    pass

VIZ_TYPE_DENYLIST = []

# Register the plugin
ANALYTICS_VIZS = [
    HighchartsChartPlugin,
]
```

## Security Checklist

- [ ] RLS policies applied to all datasets
- [ ] Guest tokens have short expiry (5-15 min)
- [ ] API key stored in environment variable, not hardcoded
- [ ] CSP headers prevent embedding on other domains
- [ ] Superset admin account has strong password
- [ ] `PUBLIC_ROLE_LIKE` set to minimal permissions
- [ ] Guest users cannot access admin endpoints
- [ ] Row-level isolation tested with SQL queries as each role

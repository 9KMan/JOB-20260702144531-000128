#!/usr/bin/env python3
"""
Guest Token API Server
Serves JWT tokens for embedded Superset dashboards.

Usage:
    python guest_token_server.py

Environment:
    SUPERSET_GUEST_SECRET - JWT signing secret (min 32 chars)
    PORT - server port (default 3000)
"""

import os
import json
import http.server
import jwt
from datetime import datetime, timedelta

PORT = int(os.getenv('PORT', 3000))
SECRET = os.getenv('SUPERSET_GUEST_SECRET', 'change-me-in-production-32-chars-min')

# Dashboard-to-tenant mapping
DASHBOARD_TENANTS = {
    'dashboard-acme-sales': 'acme',
    'dashboard-beta-sales': 'beta',
    'dashboard-all': None  # admin sees all
}

class GuestTokenHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/guest-token'):
            self.handle_guest_token()
        else:
            self.send_error(404)

    def handle_guest_token(self):
        # Parse query params
        params = http.server.parse.parse_qs(
            http.server.parse.urlparse(self.path).query or ''
        )
        tenant = params.get('tenant', [None])[0]
        dashboard_id = params.get('dashboard', [None])[0]

        # Look up RLS clause for tenant
        rls_clause = None
        if tenant:
            rls_clause = f"tenant_id = '{tenant}'"

        token = jwt.encode(
            {
                'user': {'username': 'guest'},
                'roles': ['Gamma'],
                'resources': [
                    {'type': 'dashboard', 'id': dashboard_id or 'default-dashboard'}
                ],
                'rls': [{'clause': rls_clause}] if rls_clause else [],
                'exp': datetime.utcnow() + timedelta(hours=1),
                'iat': datetime.utcnow(),
            },
            SECRET,
            algorithm='HS256'
        )

        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'token': token}).encode())

    def log_message(self, format, *args):
        print(f'[GuestToken] {format % args}')

if __name__ == '__main__':
    print(f'Starting Guest Token server on port {PORT}')
    server = http.server.HTTPServer(('0.0.0.0', PORT), GuestTokenHandler)
    server.serve_forever()

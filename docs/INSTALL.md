# Installation Guide — Ubuntu Server

Complete guide for installing, configuring, and running the Plinko game server on Ubuntu. Written for Claude Code AI agents and human operators.

## Prerequisites

- Ubuntu 20.04+ (or any Debian-based Linux)
- Python 3.8+ (ships with Ubuntu 20.04+)
- Root or sudo access
- Port 8080 available (or configure Nginx reverse proxy)

## Step 1: System Setup

```bash
sudo apt update
sudo apt install -y python3 python3-pip nginx certbot python3-certbot-nginx
```

No pip packages are required — the server uses only Python standard library modules:
`http.server`, `json`, `hashlib`, `secrets`, `urllib.request`, `os`, `datetime`

## Step 2: Deploy Game Files

### Option A: Copy from local machine
```bash
# From your local machine
scp -r game/ user@your-server:/opt/plinko/
```

### Option B: Clone from repository
```bash
cd /opt
git clone <your-repo-url> plinko
```

### Option C: Download and extract
```bash
cd /opt
wget <your-archive-url> -O plinko.tar.gz
tar xzf plinko.tar.gz
```

### Set permissions
```bash
sudo chown -R www-data:www-data /opt/plinko
chmod +x /opt/plinko/serve.py
```

## Step 3: Configure the Server

Edit `/opt/plinko/serve.py`:

```python
PORT = 8080              # Change if needed
game_balance = 1000000   # Starting balance: 1000000 = 10,000.00 (in subunits, 100 subunits = 1 unit)
```

Edit `/opt/plinko/index.html` — modify the `__OPTIONS__` object:

```javascript
window.__OPTIONS__ = {
    // Currency - change to match your platform
    "currency": "USD",
    "rules": {
        "min_bet": 100,      // 1.00 in display (subunits)
        "max_bet": 10000,    // 100.00 in display
        "currency": {
            "code": "USD",
            "symbol": "$",
            "subunits": 100,
            "exponent": 2
        }
    },
    // ... rest of options
};
```

## Step 4: Test Manually

```bash
cd /opt/plinko
python3 serve.py
```

Visit `http://your-server-ip:8080` — the game should load with the preloader, then show the Plinko board.

Press `Ctrl+C` to stop after testing.

## Step 5: Create systemd Service

Create `/etc/systemd/system/plinko.service`:

```ini
[Unit]
Description=Plinko Game Server
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/opt/plinko
ExecStart=/usr/bin/python3 /opt/plinko/serve.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ReadWritePaths=/opt/plinko
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable plinko
sudo systemctl start plinko
sudo systemctl status plinko
```

View logs:
```bash
sudo journalctl -u plinko -f
```

## Step 6: Nginx Reverse Proxy

Create `/etc/nginx/sites-available/plinko`:

```nginx
server {
    listen 80;
    server_name plinko.yourdomain.com;

    # Security headers
    add_header X-Frame-Options "ALLOWALL";  # Required for iframe embedding
    add_header X-Content-Type-Options "nosniff";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Large game assets
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
        client_max_body_size 10M;
    }

    # Cache static assets aggressively
    location ~* \.(js|css|png|jpg|jpeg|webp|gif|ico|ogg|aac|woff2?)$ {
        proxy_pass http://127.0.0.1:8080;
        proxy_cache_valid 200 30d;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/plinko /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## Step 7: SSL with Let's Encrypt

```bash
sudo certbot --nginx -d plinko.yourdomain.com
```

Certbot auto-configures Nginx for HTTPS and sets up auto-renewal.

## Step 8: Firewall

```bash
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```

## Step 9: Verify Installation

```bash
# Check service is running
sudo systemctl status plinko

# Test API
curl -s -X POST http://localhost:8080/api/Plinko/0/offline \
  -H "Content-Type: application/json" \
  -d '{"command":"init"}' | python3 -m json.tool | head -5

# Test a play round
curl -s -X POST http://localhost:8080/api/Plinko/0/offline \
  -H "Content-Type: application/json" \
  -d '{"command":"play","options":{"bet":100,"risk_level":"medium","rows":12},"extra_data":{"client_seed":42}}' \
  | python3 -m json.tool

# Test history page
curl -s http://localhost:8080/api/rounds_history/offline | head -5

# Test provably fair verification
curl -s -X POST http://localhost:8080/api/games/verify \
  -H "Content-Type: application/json" \
  -d '{"secret":"{\"outcome\":[1,0,1],\"game\":\"Plinko\",\"secret\":\"abc\"}"}' \
  | python3 -m json.tool
```

## Troubleshooting

### Port already in use
```bash
sudo lsof -i :8080
sudo kill <PID>
```

### Permission denied on assets
```bash
sudo chown -R www-data:www-data /opt/plinko
sudo chmod -R 755 /opt/plinko
```

### Missing assets (first load requires internet)
The server auto-fetches missing assets from CDN on first request and caches them locally. Ensure the server has outbound HTTPS access on first run, or pre-populate all assets.

To verify all assets are cached:
```bash
find /opt/plinko/assets -type f | wc -l
# Should be 270+ files
```

### Service won't start
```bash
sudo journalctl -u plinko -n 50 --no-pager
```

### Python version check
```bash
python3 --version
# Must be 3.8 or higher
```

## Production Considerations

1. **Balance persistence**: The current server stores balance in memory (resets on restart). For production, integrate with a database — see [INTEGRATION.md](INTEGRATION.md).

2. **Multi-player**: Each server instance maintains a single player session. For multi-player, run behind a load balancer with session affinity or integrate with your platform's user system.

3. **Rate limiting**: Add Nginx rate limiting for API endpoints:
   ```nginx
   limit_req_zone $binary_remote_addr zone=plinko_api:10m rate=10r/s;
   location /api/ {
       limit_req zone=plinko_api burst=20 nodelay;
       proxy_pass http://127.0.0.1:8080;
   }
   ```

4. **Monitoring**: The server logs all API calls to stdout/journal. Set up log rotation:
   ```bash
   sudo nano /etc/logrotate.d/plinko
   # /var/log/plinko/*.log { daily rotate 7 compress }
   ```

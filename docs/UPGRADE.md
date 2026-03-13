# Upgrade & Customization Guide

How to update the game, modify configuration, add features, and maintain the installation. Written for Claude Code AI agents to follow step-by-step.

## Table of Contents

1. [Updating the Game Engine](#updating-the-game-engine)
2. [Changing Configuration](#changing-configuration)
3. [Modifying the Paytable](#modifying-the-paytable)
4. [Adding New Features](#adding-new-features)
5. [Database Persistence](#database-persistence)
6. [Multi-Language Support](#multi-language-support)
7. [Custom Skins](#custom-skins)
8. [Scaling for Production](#scaling-for-production)

---

## Updating the Game Engine

### Check for New Versions

The current game engine version is `v0.0.57_v14.16.3`. If BGaming releases a new version:

1. Find the new bundle URL from BGaming's live game page
2. Download the new bundle:
   ```bash
   NEW_VERSION="v0.0.58_v14.17.0"  # example
   mkdir -p /opt/plinko/assets/basic/${NEW_VERSION}
   curl -o /opt/plinko/assets/basic/${NEW_VERSION}/bundle.js \
     "https://cdn.bgaming-network.com/html/Plinko/basic/${NEW_VERSION}/bundle.js"
   ```

3. Update `loader.js`:
   ```javascript
   window.SKIN_DIRS = {"basic": {root:"basic", res:"basic/${NEW_VERSION}"}};
   ```

4. Update `index.html`:
   ```javascript
   "game_bundle_source": "/assets/basic/${NEW_VERSION}/bundle.js",
   ```

5. Restart the server:
   ```bash
   sudo systemctl restart plinko
   ```

6. The CDN proxy will auto-fetch any new assets the updated bundle references.

### Updating serve.py

When modifying `serve.py`:

1. Back up the current version:
   ```bash
   cp serve.py serve.py.bak
   ```

2. Make your changes

3. Test before deploying:
   ```bash
   # Quick syntax check
   python3 -c "import py_compile; py_compile.compile('serve.py')"

   # Run verification test
   python3 -c "
   from serve import ProvablyFairEngine, PAYTABLE
   engine = ProvablyFairEngine()
   h = engine.get_next_hash()
   outcome, revealed = engine.play('42', 12)
   import hashlib
   assert hashlib.sha256(revealed['secret'].encode()).hexdigest() == h
   print('Engine OK')
   "
   ```

4. Restart:
   ```bash
   sudo systemctl restart plinko
   ```

---

## Changing Configuration

### Port

In `serve.py`:
```python
PORT = 8080  # Change to any available port
```

Or use an environment variable:
```python
PORT = int(os.environ.get("PLINKO_PORT", 8080))
```

### Starting Balance

In `serve.py`:
```python
game_balance = 1000000  # 10,000.00 in subunits
```

### Currency

In `index.html`, update all currency references in `__OPTIONS__`:
```javascript
"currency": "USD",
"rules": {
    "min_bet": 100,
    "max_bet": 10000,
    "currency": {
        "code": "USD",
        "symbol": "$",
        "subunits": 100,
        "exponent": 2
    }
}
```

Also update `handle_init()` in `serve.py` to match:
```python
"currency": {"code": "USD", "symbol": "$", "subunits": 100, "exponent": 2}
```

### Bet Limits

In both `serve.py` and `index.html`:
```python
# serve.py - handle_init()
"min_bet": 100,
"max_bet": 10000,

# serve.py - handle_play() validation
bet = max(100, min(10000, bet))  # Update these limits
```

```javascript
// index.html
"rules": {"min_bet": 100, "max_bet": 10000, ...}
```

### UI Options

In `index.html` `__OPTIONS__.ui`:
```javascript
"ui": {
    "home_button": false,          // Show/hide home button
    "full_screen_prompt": true,    // Prompt for fullscreen on mobile
    "gamble_enabled": true,        // Enable gamble feature
    "show_rtp_in_rules": true,     // Show RTP in rules panel
    "skin": "basic",               // Visual skin
    "autospin_values": ["10","25","50","100","250","500","750","1000","\u221e"]
}
```

---

## Modifying the Paytable

### Understanding the Structure

Each row count (8-16) has:
- `chances[]`: Probability of each bucket (must sum to 1.0)
- `low[]`, `medium[]`, `high[]`: Multiplier for each bucket

Array length = `rows + 1` (number of possible landing positions).

### Example: Change 16-row High Risk Max Multiplier

```python
# In serve.py PAYTABLE:
"16": {
    ...
    "high": [1000.0, 130.0, 26.0, ...]  # First value is max multiplier
    # Change 1000.0 to 500.0 to reduce max payout
}
```

### RTP Calculation

To verify RTP after paytable changes:
```python
# Calculate RTP for a specific row/risk combo
rows = "16"
risk = "high"
chances = PAYTABLE[rows]["chances"]
multipliers = PAYTABLE[rows][risk]
rtp = sum(c * m for c, m in zip(chances, multipliers))
print(f"RTP for {rows} rows {risk}: {rtp * 100:.2f}%")
```

### Full RTP Audit Script

```python
for rows in range(8, 17):
    for risk in ["low", "medium", "high"]:
        chances = PAYTABLE[str(rows)]["chances"]
        mults = PAYTABLE[str(rows)][risk]
        rtp = sum(c * m for c, m in zip(chances, mults))
        print(f"Rows {rows:2d} | {risk:6s} | RTP: {rtp*100:.4f}%")
```

---

## Adding New Features

### Adding a New API Endpoint

In `serve.py`, add to `do_POST()` or `do_GET()`:

```python
def do_POST(self):
    path = self.path

    # Add before existing routes
    if '/api/custom/leaderboard' in path:
        # Your custom logic
        self._send_json({"leaders": [...]})
        return

    # ... existing routes ...
```

### Adding Auto-Bet Limits

To enforce maximum auto-bet count server-side:

```python
# In serve.py, add to game state
auto_bet_count = 0
MAX_AUTO_BETS = 1000

# In handle_play()
auto_bet_count += 1
if auto_bet_count > MAX_AUTO_BETS:
    return {"errors": [{"code": 400, "message": "Auto-bet limit reached"}], ...}
```

### Adding Session Timeout

```python
import time

session_start = time.time()
SESSION_TIMEOUT = 3600  # 1 hour

# In handle_play()
if time.time() - session_start > SESSION_TIMEOUT:
    return {"errors": [{"code": 403, "message": "Session expired"}], ...}
```

---

## Database Persistence

### SQLite (Simple, Single-Server)

Replace in-memory state with SQLite:

```python
import sqlite3

DB_PATH = "/opt/plinko/plinko.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS state (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rounds (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            bet INTEGER,
            win INTEGER,
            profit INTEGER,
            balance_before INTEGER,
            balance_after INTEGER,
            currency TEXT,
            rows INTEGER,
            risk_level TEXT,
            multiplier REAL,
            outcome TEXT,
            bucket INTEGER,
            pre_hash TEXT,
            revealed_secret TEXT,
            client_seed TEXT
        )
    """)
    conn.commit()
    return conn

# Replace global game_balance with:
def get_balance(conn):
    row = conn.execute("SELECT value FROM state WHERE key='balance'").fetchone()
    return int(row[0]) if row else 1000000

def set_balance(conn, balance):
    conn.execute("INSERT OR REPLACE INTO state (key, value) VALUES ('balance', ?)", (str(balance),))
    conn.commit()
```

### PostgreSQL (Multi-Server)

See the schema in [INTEGRATION.md](INTEGRATION.md#database-schema-postgresql-example).

---

## Multi-Language Support

### Adding a New Language

1. Copy the English translation file:
   ```bash
   cp games-aux/translations/Plinko/en.json games-aux/translations/Plinko/es.json
   ```

2. Translate all 471 keys in the new file

3. Update `index.html`:
   ```javascript
   "locale": "es",
   ```

4. The loader.js will automatically request the correct translation file path.

### Available Translation Keys (sample)

```json
{
    "play": "Play",
    "bet": "Bet",
    "win": "Win",
    "balance": "Balance",
    "risk": "Risk",
    "rows": "Rows",
    "low": "Low",
    "medium": "Medium",
    "high": "High",
    "provability": "Provability",
    "verify": "Verify",
    "history": "History",
    ...
}
```

---

## Custom Skins

### Adding a New Skin

1. Create skin directory:
   ```bash
   mkdir -p assets/custom_skin/v1.0.0
   ```

2. Copy and modify assets (override only what you want to change):
   ```bash
   cp -r assets/basic/v0.0.57_v14.16.3/img assets/custom_skin/v1.0.0/img
   # Edit images as needed
   ```

3. Update `loader.js`:
   ```javascript
   window.SKIN_DIRS = {
       "basic": {root:"basic", res:"basic/v0.0.57_v14.16.3"},
       "custom": {root:"custom_skin", res:"custom_skin/v1.0.0"}
   };
   ```

4. Set the skin in `index.html`:
   ```javascript
   "ui": { "skin": "custom", "skins": ["basic", "custom"], ... }
   ```

---

## Scaling for Production

### Running Multiple Instances

Use a process manager like `gunicorn` or run multiple Python processes:

```bash
# Run on different ports behind a load balancer
python3 serve.py --port 8081 &
python3 serve.py --port 8082 &
python3 serve.py --port 8083 &
```

Note: Each instance has its own in-memory state. For shared state, use database persistence (see above).

### Nginx Load Balancer

```nginx
upstream plinko_backend {
    ip_hash;  # Session affinity (same player -> same server)
    server 127.0.0.1:8081;
    server 127.0.0.1:8082;
    server 127.0.0.1:8083;
}

server {
    listen 443 ssl;
    server_name plinko.yourplatform.com;

    location / {
        proxy_pass http://plinko_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### Performance Notes

- The Python server handles ~100-200 requests/second per instance
- Static assets should be served by Nginx directly for best performance:
  ```nginx
  location /assets/ {
      alias /opt/plinko/assets/;
      expires 30d;
  }
  ```
- The game engine (bundle.js) is 933KB — ensure gzip is enabled:
  ```nginx
  gzip on;
  gzip_types application/javascript text/css application/json;
  gzip_min_length 1000;
  ```

---

## Checklist: Claude Code Agent Upgrade Steps

When asked to upgrade this installation, follow this checklist:

1. [ ] Read current `serve.py` to understand existing state
2. [ ] Read current `index.html` to understand configuration
3. [ ] Back up current files: `cp serve.py serve.py.bak`
4. [ ] Make the requested changes
5. [ ] Verify Python syntax: `python3 -c "import py_compile; py_compile.compile('serve.py')"`
6. [ ] Test the provably fair engine independently
7. [ ] Restart the server: `sudo systemctl restart plinko`
8. [ ] Run a quick API test: `curl -X POST http://localhost:8080/api/Plinko/0/offline -H "Content-Type: application/json" -d '{"command":"init"}'`
9. [ ] Play a test round and verify the response
10. [ ] Check logs for errors: `sudo journalctl -u plinko -n 20`

# Platform Integration Guide

How gambling companies can integrate this Plinko game into their betting platforms. Covers iframe embedding, direct API integration, wallet hooks, multi-currency support, and multi-tenant deployment.

---

## Integration Options

| Method | Complexity | Best For |
|--------|-----------|----------|
| **iframe embed** | Low | Quick integration, isolated game |
| **Direct API** | Medium | Custom UI, mobile apps, headless betting |
| **Full backend integration** | High | Multi-player, real-money, regulated platforms |

---

## Option 1: iframe Embedding

The simplest integration. Embed the game in an iframe on your platform.

### Basic Embed

```html
<iframe
  src="https://plinko.yourplatform.com"
  width="100%"
  height="100%"
  style="border: none; min-height: 600px;"
  allow="autoplay; fullscreen"
  sandbox="allow-scripts allow-same-origin allow-popups"
></iframe>
```

### Responsive Embed

```html
<div style="position: relative; width: 100%; padding-bottom: 56.25%; overflow: hidden;">
  <iframe
    src="https://plinko.yourplatform.com"
    style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; border: none;"
    allow="autoplay; fullscreen"
  ></iframe>
</div>
```

### Passing Configuration via URL Parameters

Modify `index.html` to read URL params and override `__OPTIONS__`:

```javascript
// Add this to index.html before the game loads
const params = new URLSearchParams(window.location.search);

if (params.get('currency')) {
    window.__OPTIONS__.currency = params.get('currency');
    window.__OPTIONS__.rules.currency.code = params.get('currency');
}
if (params.get('balance')) {
    // Signal initial balance to your backend
    window.__INITIAL_BALANCE__ = parseInt(params.get('balance'));
}
if (params.get('token')) {
    // Auth token for your platform's API
    window.__PLATFORM_TOKEN__ = params.get('token');
}
if (params.get('locale')) {
    window.__OPTIONS__.locale = params.get('locale');
}
```

Usage:
```
https://plinko.yourplatform.com?currency=USD&balance=50000&token=eyJ...&locale=en
```

### Cross-Origin Communication (iframe <-> Parent)

#### Game to Platform (postMessage)

Add to `serve.py` — inject a script that posts events to the parent frame:

```javascript
// In index.html, add after game loads:
window.addEventListener('message', function(e) {
    if (e.data.type === 'GET_BALANCE') {
        // Respond with current balance
        parent.postMessage({ type: 'BALANCE', balance: currentBalance }, '*');
    }
});

// After each play round, notify parent:
function notifyParent(event, data) {
    if (window.parent !== window) {
        parent.postMessage({ type: event, ...data }, '*');
    }
}
// Call: notifyParent('ROUND_COMPLETE', { bet: 100, win: 500, balance: 99500 });
```

#### Platform to Game

```javascript
// Parent page
const gameFrame = document.getElementById('plinko-iframe');

// Update balance from platform wallet
gameFrame.contentWindow.postMessage({
    type: 'SET_BALANCE',
    balance: 50000
}, 'https://plinko.yourplatform.com');

// Listen for game events
window.addEventListener('message', function(e) {
    if (e.origin !== 'https://plinko.yourplatform.com') return;
    if (e.data.type === 'ROUND_COMPLETE') {
        console.log('Player bet:', e.data.bet, 'won:', e.data.win);
        // Update your platform's records
    }
});
```

### Nginx for iframe Embedding

```nginx
# Allow iframe embedding from your platform domain
add_header X-Frame-Options "ALLOW-FROM https://yourplatform.com";
# Or for any origin:
add_header X-Frame-Options "ALLOWALL";
# Modern browsers prefer Content-Security-Policy:
add_header Content-Security-Policy "frame-ancestors https://yourplatform.com https://*.yourplatform.com";
```

---

## Option 2: Direct API Integration

Use the Plinko server as a headless game engine. Your platform handles the UI.

### Flow

```
Player (your UI) -> Your Backend -> Plinko API -> Your Backend -> Player
```

### Your Backend Proxy Example (Node.js)

```javascript
const express = require('express');
const fetch = require('node-fetch');
const app = express();

const PLINKO_API = 'http://localhost:8080';

app.post('/api/game/play', authenticateUser, async (req, res) => {
    const { bet, risk_level, rows, client_seed } = req.body;
    const userId = req.user.id;

    // 1. Check user balance in YOUR database
    const userBalance = await db.getBalance(userId);
    if (userBalance < bet) {
        return res.status(400).json({ error: 'Insufficient balance' });
    }

    // 2. Deduct bet from YOUR database
    await db.deductBalance(userId, bet);

    // 3. Call Plinko API for the game result
    const plinkoResponse = await fetch(`${PLINKO_API}/api/Plinko/0/offline`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            command: 'play',
            options: { bet, risk_level, rows },
            extra_data: { client_seed }
        })
    });
    const result = await plinkoResponse.json();

    // 4. Credit winnings to YOUR database
    const winAmount = result.result;
    if (winAmount > 0) {
        await db.creditBalance(userId, winAmount);
    }

    // 5. Record the round in YOUR database
    await db.recordRound(userId, {
        bet, win: winAmount, risk_level, rows,
        outcome: result.game.outcome,
        provable_data: result.extra_data.provable_data
    });

    // 6. Return result to player
    res.json({
        outcome: result.game.outcome,
        win: winAmount,
        balance: userBalance - bet + winAmount,
        provable_data: result.extra_data.provable_data
    });
});
```

### Your Backend Proxy Example (Python / FastAPI)

```python
import httpx
from fastapi import FastAPI, Depends

app = FastAPI()
PLINKO_API = "http://localhost:8080"

@app.post("/api/game/play")
async def play(request: PlayRequest, user = Depends(get_current_user)):
    # 1. Check balance
    balance = await db.get_balance(user.id)
    if balance < request.bet:
        raise HTTPException(400, "Insufficient balance")

    # 2. Deduct bet
    await db.deduct_balance(user.id, request.bet)

    # 3. Call Plinko engine
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{PLINKO_API}/api/Plinko/0/offline", json={
            "command": "play",
            "options": {"bet": request.bet, "risk_level": request.risk_level, "rows": request.rows},
            "extra_data": {"client_seed": request.client_seed}
        })
        result = resp.json()

    # 4. Credit winnings
    win = result["result"]
    if win > 0:
        await db.credit_balance(user.id, win)

    # 5. Record round
    await db.record_round(user.id, result)

    return {"outcome": result["game"]["outcome"], "win": win,
            "balance": balance - request.bet + win,
            "provable_data": result["extra_data"]["provable_data"]}
```

---

## Option 3: Full Backend Integration

For regulated platforms that need the game engine embedded directly.

### Extracting the Engine

The core game logic in `serve.py` can be imported as a Python module:

```python
# In your platform's backend:
from plinko_engine import ProvablyFairEngine, PAYTABLE

# Create a per-session engine
engine = ProvablyFairEngine()

# Get the pre-game hash (show to player)
next_hash = engine.get_next_hash()

# Process a play
outcome, revealed = engine.play(client_seed_str="42", rows=12)

# Calculate win
bucket = sum(outcome)
multiplier = PAYTABLE["12"]["high"][bucket]
win = int(bet * multiplier + 0.5)

# Verify (for the verify endpoint)
computed_hash = engine.verify(revealed["secret"], "42")
assert computed_hash == revealed["hash"]
```

### Database Schema (PostgreSQL example)

```sql
CREATE TABLE plinko_rounds (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    bet INTEGER NOT NULL,
    win INTEGER NOT NULL,
    profit INTEGER GENERATED ALWAYS AS (win - bet) STORED,
    risk_level VARCHAR(6) NOT NULL CHECK (risk_level IN ('low', 'medium', 'high')),
    rows INTEGER NOT NULL CHECK (rows BETWEEN 8 AND 16),
    multiplier DECIMAL(8,2) NOT NULL,
    outcome INTEGER[] NOT NULL,
    bucket INTEGER NOT NULL,
    balance_before INTEGER NOT NULL,
    balance_after INTEGER NOT NULL,
    currency VARCHAR(10) NOT NULL DEFAULT 'USD',
    pre_game_hash VARCHAR(64) NOT NULL,
    revealed_secret TEXT NOT NULL,
    client_seed VARCHAR(20) NOT NULL,
    session_id UUID
);

CREATE INDEX idx_plinko_rounds_user ON plinko_rounds(user_id, created_at DESC);
```

### Per-Player Engine Instances

Each player needs their own `ProvablyFairEngine` instance to maintain the hash chain. Options:

1. **In-memory (Redis)**:
   ```python
   # Serialize engine state to Redis per session
   import pickle
   redis.set(f"plinko:engine:{user_id}", pickle.dumps(engine))
   engine = pickle.loads(redis.get(f"plinko:engine:{user_id}"))
   ```

2. **Database-backed**:
   ```python
   # Store next_seed, next_hash in database per user
   # Reconstruct engine from stored state on each request
   ```

3. **Stateless (recommended for scale)**:
   ```python
   # Generate seed on-the-fly, store only the hash in session
   # On play: lookup stored hash, generate outcome, verify, store next hash
   ```

---

## Multi-Currency Support

### Configuration in `index.html`

```javascript
window.__OPTIONS__.rules.currency = {
    "code": "BTC",
    "symbol": "BTC",
    "subunits": 100000000,  // satoshis
    "exponent": 8
};
```

### Common Currency Configs

| Currency | code | symbol | subunits | exponent | min_bet (subunits) | Example |
|----------|------|--------|----------|----------|--------------------|---------|
| USD | USD | $ | 100 | 2 | 100 | $1.00 |
| EUR | EUR | EUR | 100 | 2 | 100 | 1.00 EUR |
| BTC | BTC | BTC | 100000000 | 8 | 1000 | 0.00001000 BTC |
| ETH | ETH | ETH | 1000000000000000000 | 18 | 10000000000000 | 0.00001 ETH |
| USDT | USDT | USDT | 1000000 | 6 | 1000000 | 1.000000 USDT |
| FUN | FUN | FUN | 100 | 2 | 100 | 1.00 FUN |

### Adjusting Bet Limits

In both `serve.py` and `index.html`:

```python
# serve.py - handle_init() and handle_play()
"min_bet": 1000,        # Adjust per currency
"max_bet": 100000000,   # Adjust per currency
```

```javascript
// index.html
"rules": {
    "min_bet": 1000,
    "max_bet": 100000000,
    "currency": { "code": "BTC", "symbol": "BTC", "subunits": 100000000, "exponent": 8 }
}
```

---

## Wallet Integration Hooks

Modify `serve.py` to call your platform's wallet API instead of maintaining in-memory balance:

```python
import httpx

WALLET_API = "https://your-platform.com/api/wallet"
WALLET_API_KEY = os.environ.get("WALLET_API_KEY")

async def get_balance(player_token):
    resp = httpx.get(f"{WALLET_API}/balance",
                     headers={"Authorization": f"Bearer {player_token}"})
    return resp.json()["balance"]

async def debit(player_token, amount, round_id):
    resp = httpx.post(f"{WALLET_API}/debit",
                      headers={"Authorization": f"Bearer {player_token}"},
                      json={"amount": amount, "game": "plinko", "round_id": round_id})
    return resp.json()

async def credit(player_token, amount, round_id):
    resp = httpx.post(f"{WALLET_API}/credit",
                      headers={"Authorization": f"Bearer {player_token}"},
                      json={"amount": amount, "game": "plinko", "round_id": round_id})
    return resp.json()
```

---

## Multi-Tenant Deployment

Run one Plinko server per tenant, or a shared server with tenant routing:

### Docker Deployment

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE 8080
CMD ["python3", "serve.py"]
```

```yaml
# docker-compose.yml
services:
  plinko:
    build: .
    ports:
      - "8080:8080"
    environment:
      - WALLET_API_KEY=${WALLET_API_KEY}
    restart: always
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: plinko
spec:
  replicas: 3
  selector:
    matchLabels:
      app: plinko
  template:
    metadata:
      labels:
        app: plinko
    spec:
      containers:
      - name: plinko
        image: your-registry/plinko:latest
        ports:
        - containerPort: 8080
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "500m"
```

---

## Regulatory Compliance

### Provably Fair Audit Trail

Every round produces:
1. Pre-game SHA-256 hash (shown before play)
2. Post-game revealed secret (verifiable by anyone)
3. Client seed (player-provided, stored)
4. Full 32-bit result array
5. Game outcome (first N bits after rotation)

This data satisfies provably fair requirements for most jurisdictions. Store all fields in your database for audit purposes.

### RTP Verification

The paytable produces these verified RTPs:
- **Main RTP**: 98.91%
- **Min RTP**: 98.91%
- **Max RTP**: 99.16%

These can be independently verified by running the probability calculations against the paytable multipliers and chances arrays.

### Session Logging

The server logs all API calls to stdout. In production, pipe to your logging infrastructure:

```bash
# journalctl (systemd)
sudo journalctl -u plinko -f

# Or redirect to file
python3 serve.py 2>&1 | tee -a /var/log/plinko/game.log
```

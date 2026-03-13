# API Reference

Complete specification of every endpoint the Plinko server exposes. All API calls use JSON over HTTP.

## Base URL

```
http://localhost:8080
```

## Authentication

The current server has no authentication. For production integration, add your platform's auth layer (JWT, API keys, session tokens) — see [INTEGRATION.md](INTEGRATION.md).

---

## Game API

### POST `/api/Plinko/0/offline`

The main game endpoint. All game commands go through this single endpoint using a `command` field.

#### Headers
```
Content-Type: application/json
X-CSRF-Token: offline-token    (optional, configured in index.html __OPTIONS__)
```

---

### Command: `init`

Initialize the game session. Returns paytable, balance, and the first provably fair hash.

#### Request
```json
{
  "command": "init"
}
```

#### Response
```json
{
  "options": {
    "min_bet": 100,
    "max_bet": 10000,
    "default_bet": 100,
    "currency": {
      "code": "FUN",
      "symbol": "FUN",
      "subunits": 100,
      "exponent": 2
    },
    "risk_levels": ["low", "medium", "high"]
  },
  "paytable": {
    "8": {
      "chances": [0.00390625, 0.03125, ...],
      "low": [5.6, 2.1, 1.1, 1.0, 0.5, 1.0, 1.1, 2.1, 5.6],
      "medium": [13.0, 3.0, 1.3, 0.7, 0.4, 0.7, 1.3, 3.0, 13.0],
      "high": [29.0, 4.0, 1.5, 0.3, 0.2, 0.3, 1.5, 4.0, 29.0]
    },
    "9": { ... },
    "10": { ... },
    "11": { ... },
    "12": { ... },
    "13": { ... },
    "14": { ... },
    "15": { ... },
    "16": { ... }
  },
  "game": {
    "state": "idle"
  },
  "balance": 1000000,
  "extra_data": {
    "provable_data": [
      {
        "hash": "a3f880ff2c06d8aef8fe242f6387452b630f6dae80aae98c6ca879593b..."
      }
    ]
  },
  "available_commands": ["init", "play"],
  "requested_command": "init"
}
```

#### Key Fields
- `balance`: Player balance in subunits (divide by 100 for display: `1000000` = `10,000.00`)
- `paytable`: Keys are row counts `"8"` through `"16"`. Each contains `chances` (probability array), `low`, `medium`, `high` (multiplier arrays)
- `extra_data.provable_data[0].hash`: SHA-256 hash commitment for the NEXT round (shown to player before they play)

---

### Command: `play`

Drop a ball. Deducts the bet, generates a provably fair outcome, calculates the win, and returns the result.

#### Request
```json
{
  "command": "play",
  "options": {
    "bet": 500,
    "risk_level": "high",
    "rows": 16
  },
  "extra_data": {
    "client_seed": 42
  }
}
```

#### Parameters
| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `options.bet` | int | 100 - 10000 | Bet amount in subunits |
| `options.risk_level` | string | `"low"`, `"medium"`, `"high"` | Risk level (affects multipliers) |
| `options.rows` | int | 8 - 16 | Number of pin rows |
| `extra_data.client_seed` | int/string | any integer | Client-provided seed for provably fair rotation |

#### Response (success)
```json
{
  "bets": {
    "bet": 500,
    "risk_level": "high",
    "rows": 16
  },
  "game": {
    "outcome": [0, 1, 1, 0, 0, 1, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1],
    "state": "closed",
    "action": "play"
  },
  "result": 100,
  "balance": 999600,
  "extra_data": {
    "provable_data": [
      {
        "hash": "next_round_hash_here..."
      },
      {
        "hash": "this_round_hash_here...",
        "secret": "{\"outcome\":[1,0,1,...],\"game\":\"Plinko\",\"secret\":\"926825cfd3efb8da\"}",
        "client_seed": "42",
        "result": "[0,1,1,0,0,1,0,1,1,0,0,1,0,0,1,1,...]"
      }
    ]
  },
  "available_commands": ["init", "play"],
  "requested_command": "play"
}
```

#### Key Fields
- `game.outcome`: Array of 0s and 1s. Length = `rows`. `0` = ball goes left, `1` = ball goes right at each pin row
- `result`: Win amount in subunits
- `balance`: Updated balance after bet deduction and win addition
- `extra_data.provable_data[0]`: Hash for the NEXT round
- `extra_data.provable_data[1]`: Revealed data for THIS round (hash, secret JSON, client_seed, full 32-bit result)

#### Response (insufficient balance — error 301)
```json
{
  "errors": [{"code": 301}],
  "balance": 50,
  "game": {"state": "idle"},
  "available_commands": ["init", "play"],
  "requested_command": "play"
}
```

#### Win Calculation
```
bucket_index = sum(outcome)           // count of 1s in outcome
multiplier = paytable[rows][risk_level][bucket_index]
win = int(bet * multiplier + 0.5)     // JavaScript-compatible rounding
new_balance = old_balance - bet + win
```

---

### Command: `close_session`

Close the game session. Optional cleanup.

#### Request
```json
{
  "command": "close_session"
}
```

#### Response
```json
{
  "success": true
}
```

---

## Verify API

### POST `/api/games/verify`

Verify a provably fair result by recomputing the SHA-256 hash of the revealed secret.

#### Request
```json
{
  "secret": "{\"outcome\":[1,0,1,...],\"game\":\"Plinko\",\"secret\":\"926825cfd3efb8da\"}",
  "client_seed": "42"
}
```

#### Response
```json
{
  "hash": "a38212a3f880ff2c06d8aef8fe242f6387452b630f6dae80aae98c6ca879593b"
}
```

The client compares this `hash` against the hash that was shown BEFORE the round was played. If they match, the round was fair.

---

## Rounds History

### GET `/api/rounds_history/offline`

Returns an HTML page listing all played rounds with a table of Date/Time, Bet, Total Win, Profit, Balance Before, Balance After, Currency, and a link to view round details.

### GET `/api/rounds_history/-/{round_id}`

Returns an HTML page showing a specific round's details including:
- Round metadata (date, bet, win, profit, balances, currency)
- Visual Plinko board with ball path (pin grid + directional arrows)
- Multiplier row with landing bucket highlighted
- Bet and win amounts

---

## Static Assets

### GET `/assets/*`

Serves game assets (JS, images, sounds). If a file is not found locally, the server fetches it from the BGaming CDN, caches it locally, and serves it. Subsequent requests are served from the local cache.

### GET `/games-aux/*`

Serves game rules and translations. Same CDN proxy + cache behavior as `/assets/*`.

### GET `/index.html` (or `/`)

The main game HTML page.

---

## Error Codes

| Code | Meaning | When |
|------|---------|------|
| 301 | Insufficient balance | Bet amount exceeds current balance |

---

## Data Types

### Balance / Bet / Win
All monetary values are integers in **subunits**. With `exponent: 2`:
- `100` subunits = `1.00` display
- `10000` subunits = `100.00` display
- `1000000` subunits = `10,000.00` display

### Outcome Array
Array of `0` and `1` integers:
- `0` = ball bounces left at this pin row
- `1` = ball bounces right at this pin row
- Length equals the number of rows selected

### Paytable Structure
For each row count (8-16):
- `chances[]`: Probability of landing in each bucket (sums to 1.0)
- `low[]`: Multipliers for low risk
- `medium[]`: Multipliers for medium risk
- `high[]`: Multipliers for high risk
- Array length = rows + 1 (number of buckets)

### Provable Data
- `provable_data[0]`: Always contains `{hash}` for the NEXT round
- `provable_data[1]`: Present only in play responses — revealed data for the JUST-PLAYED round

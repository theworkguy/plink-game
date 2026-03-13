# Architecture

How the Plinko game works end-to-end: frontend, backend, asset pipeline, and data flow.

## System Overview

```
Browser                          Server (serve.py)
  |                                   |
  |  GET /index.html                  |
  |<----------------------------------|  Serves bootstrapper HTML
  |                                   |
  |  GET /loader.js                   |
  |<----------------------------------|  Patched loader (local paths)
  |                                   |
  |  GET /assets/.../bundle.js        |
  |<----------------------------------|  Game engine (933KB PixiJS app)
  |                                   |
  |  POST {command:"init"}            |
  |<----------------------------------|  Paytable + balance + first hash
  |                                   |
  |  GET /assets/.../img/*.png        |
  |<----------------------------------|  Game images (local or CDN proxy)
  |                                   |
  |  GET /assets/.../snd/*.ogg        |
  |<----------------------------------|  Sound files
  |                                   |
  |  POST {command:"play",...}        |
  |<----------------------------------|  Outcome + win + provable data
  |                                   |
  |  POST /api/games/verify           |
  |<----------------------------------|  Hash verification
  |                                   |
  |  GET /api/rounds_history/offline  |
  |<----------------------------------|  History HTML page
```

## File Map

### Core Files (you modify these)

| File | Purpose | Size |
|------|---------|------|
| `serve.py` | Python game server — API handlers, provably fair engine, CDN proxy, history pages | ~580 lines |
| `index.html` | Game bootstrapper — loads scripts, configures `__OPTIONS__`, blocks analytics | ~165 lines |
| `loader.js` | Asset path resolver — patched for local paths instead of CDN URLs | ~7 lines (minified) |

### Game Engine (do NOT modify)

| File | Purpose | Size |
|------|---------|------|
| `assets/basic/v0.0.57_v14.16.3/bundle.js` | Complete game engine — PixiJS renderer, game logic, UI, animations, sound | 933KB |

This is the original BGaming game engine. It is minified and must not be modified. All customization happens through `__OPTIONS__`, `serve.py` API responses, and CSS.

### Static Assets

| Directory | Contents | Count |
|-----------|----------|-------|
| `assets/basic/v0.0.57_v14.16.3/img/` | All game images | ~255 files |
| `assets/basic/v0.0.57_v14.16.3/img/bg/` | Background images | 8 files |
| `assets/basic/v0.0.57_v14.16.3/img/ui/` | UI buttons, icons, controls | ~175 files |
| `assets/basic/v0.0.57_v14.16.3/img/ui/provability/` | Provably fair UI elements | 36 files |
| `assets/basic/v0.0.57_v14.16.3/snd/` | Sound effects + music | 14 files |
| `assets/basic/v0.0.57_v14.16.3/preloader-assets/` | Loading screen spinner, logo | 12 files |

### Game Data

| File | Purpose |
|------|---------|
| `games-aux/rules/en/Plinko.json` | Game rules (HTML content displayed in rules panel) |
| `games-aux/translations/Plinko/en.json` | English translations (471 keys — all UI text) |
| `init_data.json` | Reference capture of original BGaming init response |
| `rules.json` | Game rules definition |

### Reference Files

| File | Purpose |
|------|---------|
| `original_page.html` | Original BGaming HTML page (reference for comparison) |

## Frontend Architecture

### Boot Sequence

1. Browser loads `index.html`
2. `index.html` sets `window.__OPTIONS__` (game configuration)
3. `index.html` blocks WebSocket, sendBeacon, analytics URLs
4. `loader.js` executes:
   - Sets `SKIN_DIRS` for asset path resolution
   - Constructs `rules_url` and `localization_url` from local paths
   - Calls `initializeCasinoOptions()` to finalize paths
5. `bundle.js` loads and initializes the PixiJS game
6. Game sends `POST {command: "init"}` to get paytable and balance
7. Game renders the Plinko board and UI

### Game Engine Internals

The bundle.js game engine:
- Uses **PixiJS** for rendering (WebGL/Canvas)
- Manages game state machine: `idle` -> `playing` -> `closed` -> `idle`
- Sends API calls via `Tr.fetch()` (wrapper around native `fetch()`)
- Uses `Er.A.promise` for game-loop-based promise resolution
- Processes `available_commands` array into capability flags
- Auto-generates `flow` from `{state, available_actions, command}` if not in response
- Reads `casinoOptions.history_url` to show/hide history button
- Reads `casinoOptions.actions.return` to show/hide home button

### Key __OPTIONS__ Fields

```javascript
{
    "api": "/api/Plinko/0/offline",           // API endpoint path
    "currency": "FUN",                         // Currency code
    "resources_path": "/assets",               // Base path for assets
    "game_bundle_source": "/assets/.../bundle.js",  // Game engine path
    "rules_url": "/games-aux/rules/en/Plinko.json",
    "provable_fair": {"verify_url": "/api/games/verify"},
    "math": {"rtp": {"main": 98.91}, "max_multiplier": 1000.0},
    "rules": {"min_bet": 100, "max_bet": 10000, "currency": {...}},
    "actions": {
        "history": {"text": null, "link": "/api/rounds_history/offline", "mode": "open"}
    },
    "ui": {"skin": "basic", "gamble_enabled": true, "show_rtp_in_rules": true}
}
```

### Blocked External Calls

The `index.html` interceptors block these patterns:
- **WebSocket**: All connections (no WS server needed)
- **sendBeacon**: All calls (analytics)
- **fetch/XHR URLs matching**: `cable|lobby|drops|replays|boost2|amplitude|googletagmanager|gtag|bgaming-system|challenges|quests`

All game API calls (`/api/Plinko/`, `/api/games/verify`) pass through to `serve.py`.

## Backend Architecture

### serve.py Components

```
serve.py
├── PAYTABLE                    # 9 row configs x 3 risk levels = 27 multiplier arrays
├── ProvablyFairEngine          # Cryptographic game engine
│   ├── _generate_next_seed()   # Creates 32 random bits + secret + SHA-256 hash
│   ├── get_next_hash()         # Returns pre-game hash commitment
│   ├── play()                  # Rotates outcome, returns game result + revealed data
│   └── verify()                # Recomputes SHA-256 for verification
├── Game State                  # balance, rounds_history, round_counter
├── API Handlers
│   ├── handle_init()           # Returns paytable, balance, first hash
│   ├── handle_play()           # Processes bet, calculates win, records history
│   └── handle_verify()         # Hash verification endpoint
├── HTML Generators
│   ├── generate_history_html()       # Rounds history list page
│   └── generate_round_detail_html()  # Individual round detail with board visualization
└── PlinkoHandler (HTTP Server)
    ├── do_GET()                # Static files + CDN proxy + history pages
    ├── do_POST()               # API routing
    ├── guess_type()            # MIME type overrides (UTF-8 charset)
    └── CDN proxy               # Auto-fetch and cache missing assets
```

### Request Flow: Play

```
1. Client POST {command:"play", options:{bet,risk,rows}, extra_data:{client_seed}}
2. handle_play() validates bet, risk_level, rows
3. Check balance >= bet (error 301 if insufficient)
4. engine.play(client_seed, rows):
   a. Uses pre-generated seed (outcome + secret + hash)
   b. Rotates outcome by client_seed % 32
   c. Takes first N values as game_outcome
   d. Packages revealed data (hash, secret_json, client_seed, full result)
   e. Generates NEXT seed for future round
5. Calculate bucket = sum(outcome), lookup multiplier, compute win
6. Update balance: balance = balance - bet + win
7. Append to rounds_history
8. Return JSON response with outcome, win, balance, provable_data
```

### CDN Proxy Flow

```
1. Client requests GET /assets/basic/v0.0.57_v14.16.3/img/ui/bet-btn.png
2. Server checks if file exists locally
3. If YES: serve from disk (fast)
4. If NO:
   a. Construct CDN URL: https://cdn.bgaming-network.com/html/Plinko/basic/v0.0.57_v14.16.3/img/ui/bet-btn.png
   b. Fetch from CDN
   c. Save to local disk (cache for future)
   d. Serve to client
   e. Log: [CDN] cached assets/basic/v0.0.57_v14.16.3/img/ui/bet-btn.png (1234 bytes)
```

## Data Flow

### Balance Tracking

```
Initial: 1,000,000 subunits (10,000.00 FUN)

Round 1: bet=500, multiplier=x0.2, win=100
  Balance: 1,000,000 - 500 + 100 = 999,600

Round 2: bet=1000, multiplier=x3.0, win=3000
  Balance: 999,600 - 1000 + 3000 = 1,001,600
```

### Provably Fair Chain

```
Init:  hash_1 (commitment for round 1)
Play:  reveal secret_1 + hash_2 (commitment for round 2)
Play:  reveal secret_2 + hash_3 (commitment for round 3)
...each round reveals the previous secret and commits to the next
```

## Image Format Notes

Many game images use a naming convention with dimensions and format conversion:
```
ball.png_80_80.webp        # ball.png converted to 80x80 webp
bg.jpg_1920_1080.webp      # bg.jpg converted to 1920x1080 webp
```

The bundle.js handles these naming conventions internally. The CDN proxy caches them with their exact filenames.

## Character Encoding

The bundle.js uses UTF-8 for multiplier labels (the multiplication sign is `\u00D7` = `×`). The server must serve `.js` files with `charset=utf-8` in the Content-Type header, otherwise the character renders incorrectly. This is handled by `MIME_OVERRIDES` in `serve.py`.

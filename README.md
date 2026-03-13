# Plinko - Self-Hosted Provably Fair Game Server

A fully self-contained Plinko game with a Python backend implementing real provably fair cryptography (SHA-256 + rotation algorithm). Identical gameplay, visuals, sounds, and verification to the original BGaming Plinko. Zero external dependencies at runtime — runs 100% offline after initial asset cache.

## Quick Start (Ubuntu Server)

```bash
# 1. Install Python 3.8+
sudo apt update && sudo apt install -y python3 python3-pip

# 2. Clone or copy the game directory to your server
scp -r game/ user@your-server:/opt/plinko/

# 3. Start the server
cd /opt/plinko
python3 serve.py

# 4. Open in browser
# http://your-server-ip:8080
```

The server starts on port 8080 with no dependencies beyond Python's standard library.

## What This Is

- Complete Plinko game engine (PixiJS-based frontend, Python API backend)
- Provably fair: SHA-256 hash commitment + array rotation — cryptographically verifiable
- All row counts (8-16), all risk levels (low/medium/high), full paytable
- Rounds history with per-round detail pages and visual ball path
- Auto-caching CDN proxy for any missing assets on first load
- Verified with 405+ automated rounds across all configurations — zero failures

## Documentation

All detailed documentation is in the [`docs/`](docs/) folder:

| Document | Description |
|----------|-------------|
| [docs/INSTALL.md](docs/INSTALL.md) | Full Ubuntu server installation, systemd service, Nginx reverse proxy, SSL |
| [docs/API.md](docs/API.md) | Complete API reference — every endpoint, request/response format, error codes |
| [docs/PROVABLY-FAIR.md](docs/PROVABLY-FAIR.md) | Cryptographic algorithm specification, verification steps, code examples |
| [docs/INTEGRATION.md](docs/INTEGRATION.md) | How to embed in gambling platforms — iframe, API, wallet hooks, multi-currency |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Project structure, file map, how the frontend/backend interact |
| [docs/UPGRADE.md](docs/UPGRADE.md) | How to update, add features, change paytables, modify configuration |

## Project Structure

```
game/
├── serve.py                  # Python game server (API + static files + CDN proxy)
├── index.html                # Game bootstrapper HTML
├── loader.js                 # Patched game loader (local path resolution)
├── init_data.json            # Reference API init response
├── rules.json                # Game rules definition
├── original_page.html        # Original BGaming page (reference only)
├── docs/                     # Full documentation
├── assets/
│   └── basic/v0.0.57_v14.16.3/
│       ├── bundle.js         # Game engine (933KB, PixiJS-based, untouched)
│       ├── img/              # All game images (255 files)
│       │   ├── bg/           # Backgrounds
│       │   ├── ui/           # UI elements (buttons, icons)
│       │   └── provability/  # Provably fair UI assets
│       ├── snd/              # Sound files (ogg + aac)
│       └── preloader-assets/ # Loading screen assets
└── games-aux/
    ├── rules/en/Plinko.json       # Game rules (HTML content)
    └── translations/Plinko/en.json # English translations (471 keys)
```

## Configuration

Edit the top of `serve.py`:

```python
PORT = 8080              # Server port
game_balance = 1000000   # Starting balance in subunits (1000000 = 10,000.00 FUN)
```

Edit `index.html` `__OPTIONS__` for:
- Currency code/symbol
- Min/max bet limits
- UI skin settings
- Locale

## License

This project is for educational and authorized testing purposes only.

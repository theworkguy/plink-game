"""
BGaming Plinko - Full Offline Server
Implements the complete BGaming API with real provably fair cryptography.
All assets served locally with CDN auto-cache on first load.
"""
import http.server
import json
import os
import hashlib
import secrets
import urllib.request
import urllib.error
from urllib.parse import urlparse, parse_qs
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)))
PORT = int(os.environ.get("PORT", 8080))
CDN_BASE = "https://cdn.bgaming-network.com/html/Plinko"

# ═══════════════════════════════════════════════════════
# PAYTABLE - Exact copy from BGaming API
# ═══════════════════════════════════════════════════════
PAYTABLE = {
    "8":{"chances":[0.00390625,0.03125,0.109375,0.21875,0.2734375,0.21875,0.109375,0.03125,0.00390625],"low":[5.6,2.1,1.1,1.0,0.5,1.0,1.1,2.1,5.6],"medium":[13.0,3.0,1.3,0.7,0.4,0.7,1.3,3.0,13.0],"high":[29.0,4.0,1.5,0.3,0.2,0.3,1.5,4.0,29.0]},
    "9":{"chances":[0.001953125,0.017578125,0.0703125,0.1640625,0.24609375,0.24609375,0.1640625,0.0703125,0.017578125,0.001953125],"low":[5.6,2.0,1.6,1.0,0.7,0.7,1.0,1.6,2.0,5.6],"medium":[18.0,4.0,1.7,0.9,0.5,0.5,0.9,1.7,4.0,18.0],"high":[43.0,7.0,2.0,0.6,0.2,0.2,0.6,2.0,7.0,43.0]},
    "10":{"chances":[0.0009765625,0.009765625,0.0439453125,0.1171875,0.205078125,0.24609375,0.205078125,0.1171875,0.0439453125,0.009765625,0.0009765625],"low":[8.9,3.0,1.4,1.1,1.0,0.5,1.0,1.1,1.4,3.0,8.9],"medium":[22.0,5.0,2.0,1.4,0.6,0.4,0.6,1.4,2.0,5.0,22.0],"high":[76.0,10.0,3.0,0.9,0.3,0.2,0.3,0.9,3.0,10.0,76.0]},
    "11":{"chances":[0.00048828125,0.00537109375,0.02685546875,0.08056640625,0.1611328125,0.2255859375,0.2255859375,0.1611328125,0.08056640625,0.02685546875,0.00537109375,0.00048828125],"low":[8.4,3.0,1.9,1.3,1.0,0.7,0.7,1.0,1.3,1.9,3.0,8.4],"medium":[24.0,6.0,3.0,1.8,0.7,0.5,0.5,0.7,1.8,3.0,6.0,24.0],"high":[120.0,14.0,5.2,1.4,0.4,0.2,0.2,0.4,1.4,5.2,14.0,120.0]},
    "12":{"chances":[0.000244140625,0.0029296875,0.01611328125,0.0537109375,0.120849609375,0.193359375,0.2255859375,0.193359375,0.120849609375,0.0537109375,0.01611328125,0.0029296875,0.000244140625],"low":[10.0,3.0,1.6,1.4,1.1,1.0,0.5,1.0,1.1,1.4,1.6,3.0,10.0],"medium":[33.0,11.0,4.0,2.0,1.1,0.6,0.3,0.6,1.1,2.0,4.0,11.0,33.0],"high":[170.0,24.0,8.1,2.0,0.7,0.2,0.2,0.2,0.7,2.0,8.1,24.0,170.0]},
    "13":{"chances":[0.0001220703125,0.0015869140625,0.009521484375,0.034912109375,0.0872802734375,0.1571044921875,0.20947265625,0.20947265625,0.1571044921875,0.0872802734375,0.034912109375,0.009521484375,0.0015869140625,0.0001220703125],"low":[8.1,4.0,3.0,1.9,1.2,0.9,0.7,0.7,0.9,1.2,1.9,3.0,4.0,8.1],"medium":[43.0,13.0,6.0,3.0,1.3,0.7,0.4,0.4,0.7,1.3,3.0,6.0,13.0,43.0],"high":[260.0,37.0,11.0,4.0,1.0,0.2,0.2,0.2,0.2,1.0,4.0,11.0,37.0,260.0]},
    "14":{"chances":[0.00006103515625,0.0008544921875,0.00555419921875,0.022216796875,0.06109619140625,0.1221923828125,0.18328857421875,0.20947265625,0.18328857421875,0.1221923828125,0.06109619140625,0.022216796875,0.00555419921875,0.0008544921875,0.00006103515625],"low":[7.1,4.0,1.9,1.4,1.3,1.1,1.0,0.5,1.0,1.1,1.3,1.4,1.9,4.0,7.1],"medium":[58.0,15.0,7.0,4.0,1.9,1.0,0.5,0.2,0.5,1.0,1.9,4.0,7.0,15.0,58.0],"high":[420.0,56.0,18.0,5.0,1.9,0.3,0.2,0.2,0.2,0.3,1.9,5.0,18.0,56.0,420.0]},
    "15":{"chances":[0.000030517578125,0.000457763671875,0.003204345703125,0.013885498046875,0.041656494140625,0.091644287109375,0.152740478515625,0.196380615234375,0.196380615234375,0.152740478515625,0.091644287109375,0.041656494140625,0.013885498046875,0.003204345703125,0.000457763671875,0.000030517578125],"low":[15.0,8.0,3.0,2.0,1.5,1.1,1.0,0.7,0.7,1.0,1.1,1.5,2.0,3.0,8.0,15.0],"medium":[88.0,18.0,11.0,5.0,3.0,1.3,0.5,0.3,0.3,0.5,1.3,3.0,5.0,11.0,18.0,88.0],"high":[620.0,83.0,27.0,8.0,3.0,0.5,0.2,0.2,0.2,0.2,0.5,3.0,8.0,27.0,83.0,620.0]},
    "16":{"chances":[0.0000152587890625,0.000244140625,0.0018310546875,0.008544921875,0.02777099609375,0.066650390625,0.1221923828125,0.174560546875,0.196380615234375,0.174560546875,0.1221923828125,0.066650390625,0.02777099609375,0.008544921875,0.0018310546875,0.000244140625,0.0000152587890625],"low":[16.0,9.0,2.0,1.4,1.4,1.2,1.1,1.0,0.5,1.0,1.1,1.2,1.4,1.4,2.0,9.0,16.0],"medium":[110.0,41.0,10.0,5.0,3.0,1.5,1.0,0.5,0.3,0.5,1.0,1.5,3.0,5.0,10.0,41.0,110.0],"high":[1000.0,130.0,26.0,9.0,4.0,2.0,0.2,0.2,0.2,0.2,0.2,2.0,4.0,9.0,26.0,130.0,1000.0]}
}

# ═══════════════════════════════════════════════════════
# PROVABLY FAIR ENGINE
# Exact same algorithm as BGaming:
#   1. Generate 32 random bits (server_outcome)
#   2. Create secret_json = {"outcome": bits, "game": "Plinko", "secret": random_hex}
#   3. hash = SHA256(secret_json)
#   4. On play: rotate server_outcome by client_seed positions
#   5. Game outcome = first N values of rotated array
#   6. Verify: SHA256(secret_json) must match pre-game hash
# ═══════════════════════════════════════════════════════

class ProvablyFairEngine:
    def __init__(self):
        self.next_seed = None
        self.next_hash = None
        self.previous_seed_data = None
        self._generate_next_seed()

    def _generate_next_seed(self):
        outcome = [secrets.randbelow(2) for _ in range(32)]
        secret_hex = secrets.token_hex(16)
        seed_data = {
            "outcome": outcome,
            "game": "Plinko",
            "secret": secret_hex
        }
        # Must match BGaming's exact JSON format (no spaces after separators)
        seed_json = json.dumps(seed_data, separators=(',', ':'))
        seed_hash = hashlib.sha256(seed_json.encode()).hexdigest()

        self.next_seed = seed_data
        self.next_seed_json = seed_json
        self.next_hash = seed_hash

    def get_next_hash(self):
        return self.next_hash

    def play(self, client_seed_str, rows):
        # Current game uses the prepared seed
        current_seed = self.next_seed
        current_seed_json = self.next_seed_json
        current_hash = self.next_hash

        # Parse client seed as integer for rotation
        try:
            rotation = int(client_seed_str) % 32
        except (ValueError, TypeError):
            rotation = 0

        # Rotate outcome by client_seed positions (BGaming algorithm)
        server_outcome = current_seed["outcome"]
        result = server_outcome[rotation:] + server_outcome[:rotation]

        # Game outcome = first N values
        game_outcome = result[:rows]

        # Prepare the revealed data for this game
        revealed = {
            "hash": current_hash,
            "secret": current_seed_json,
            "client_seed": client_seed_str,
            "result": json.dumps(result, separators=(',', ':'))
        }

        # Generate next seed for future game
        self._generate_next_seed()

        return game_outcome, revealed

    def verify(self, secret_json, client_seed_str):
        computed_hash = hashlib.sha256(secret_json.encode()).hexdigest()
        return computed_hash


# ═══════════════════════════════════════════════════════
# GAME STATE
# ═══════════════════════════════════════════════════════
engine = ProvablyFairEngine()
game_balance = 1000000  # 10,000.00 FUN
rounds_history = []     # List of round records for history page
round_counter = 0       # Round ID counter

SEED_LIMITS = "Client seed can be 0-31"


# ═══════════════════════════════════════════════════════
# API HANDLERS
# ═══════════════════════════════════════════════════════

def handle_init():
    global game_balance
    return {
        "options": {
            "min_bet": 100,
            "max_bet": 10000,
            "default_bet": 100,
            "currency": {"code": "FUN", "symbol": "FUN", "subunits": 100, "exponent": 2},
            "risk_levels": ["low", "medium", "high"]
        },
        "paytable": PAYTABLE,
        "game": {"state": "idle"},
        "balance": game_balance,
        "extra_data": {
            "provable_data": [
                {"hash": engine.get_next_hash()}
            ]
        },
        "available_commands": ["init", "play"],
        "requested_command": "init"
    }


def handle_play(options, extra_data):
    global game_balance, round_counter

    bet = options.get("bet", 100)
    risk_level = options.get("risk_level", "low")
    rows = options.get("rows", 8)

    # Validate bet is within limits
    bet = max(100, min(10000, bet))

    # Check sufficient balance (error 301 = insufficient funds)
    if game_balance < bet:
        return {
            "errors": [{"code": 301}],
            "balance": game_balance,
            "game": {"state": "idle"},
            "available_commands": ["init", "play"],
            "requested_command": "play"
        }

    # Validate risk_level and rows
    if risk_level not in ("low", "medium", "high"):
        risk_level = "low"
    if str(rows) not in PAYTABLE:
        rows = 8

    # Get client seed
    client_seed_str = "0"
    if extra_data and "client_seed" in extra_data:
        cs = extra_data["client_seed"]
        if isinstance(cs, list):
            client_seed_str = "".join(str(x) for x in cs)
        else:
            client_seed_str = str(cs)

    # Record balance before bet
    balance_before = game_balance

    # Generate outcome using provably fair engine
    game_outcome, revealed_data = engine.play(client_seed_str, rows)

    # Calculate win (use int() to match JavaScript Math.round behavior for positive numbers)
    bucket_index = sum(game_outcome)
    multiplier = PAYTABLE[str(rows)][risk_level][bucket_index]
    win_amount = int(bet * multiplier + 0.5)

    # Update balance
    game_balance -= bet
    game_balance += win_amount

    # Record round in history
    round_counter += 1
    rounds_history.append({
        "id": round_counter,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "bet": bet,
        "win": win_amount,
        "profit": win_amount - bet,
        "balance_before": balance_before,
        "balance_after": game_balance,
        "currency": "FUN",
        "rows": rows,
        "risk_level": risk_level,
        "multiplier": multiplier,
        "outcome": game_outcome,
        "bucket": bucket_index
    })

    return {
        "bets": {"bet": bet, "risk_level": risk_level, "rows": rows},
        "game": {
            "outcome": game_outcome,
            "state": "closed",
            "action": "play"
        },
        "result": win_amount,
        "balance": game_balance,
        "extra_data": {
            "provable_data": [
                {"hash": engine.get_next_hash()},
                revealed_data
            ]
        },
        "available_commands": ["init", "play"],
        "requested_command": "play"
    }


def handle_verify(body):
    secret = body.get("secret", "")
    computed_hash = engine.verify(secret, body.get("client_seed", "0"))
    return {"hash": computed_hash}


def generate_history_html():
    """Generate HTML page matching BGaming's rounds history format."""
    rows_html = ""
    for r in reversed(rounds_history):
        bet_display = f"{r['bet']/100:.2f}"
        win_display = f"{r['win']/100:.2f}"
        profit_val = r['profit'] / 100
        profit_display = f"{profit_val:+.2f}" if profit_val != 0 else "0.00"
        profit_class = "positive" if profit_val > 0 else ("negative" if profit_val < 0 else "")
        bal_before = f"{r['balance_before']/100:.2f}"
        bal_after = f"{r['balance_after']/100:.2f}"
        detail_link = f"/api/rounds_history/-/{r['id']}"
        rows_html += f"""        <tr>
          <td>{r['timestamp']}</td>
          <td>{bet_display}</td>
          <td>{win_display}</td>
          <td class="{profit_class}">{profit_display}</td>
          <td>{bal_before}</td>
          <td>{bal_after}</td>
          <td>{r['currency']}</td>
          <td><a href="{detail_link}">View Details</a></td>
        </tr>\n"""

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Plinko: Games History</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #1a1a2e; color: #e0e0e0; padding: 20px; }}
  h1 {{ text-align: center; margin-bottom: 20px; font-size: 22px; color: #fff; }}
  .summary {{ text-align: center; margin-bottom: 16px; font-size: 14px; color: #aaa; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  th {{ background: #16213e; color: #e94560; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; padding: 10px 8px; text-align: left; border-bottom: 2px solid #0f3460; }}
  td {{ padding: 8px; border-bottom: 1px solid #16213e; }}
  tr:hover {{ background: #16213e; }}
  .positive {{ color: #4ecca3; }}
  .negative {{ color: #e94560; }}
  .empty {{ text-align: center; padding: 40px; color: #666; font-size: 16px; }}
  a {{ color: #e94560; text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
</style>
</head>
<body>
<h1>Plinko: Games History</h1>
<div class="summary">{len(rounds_history)} round{"s" if len(rounds_history) != 1 else ""} played</div>
{"<table><thead><tr><th>Date/Time</th><th>Bet</th><th>Total Win</th><th>Profit</th><th>Balance Before</th><th>Balance After</th><th>Currency</th><th>Round Details</th></tr></thead><tbody>" + rows_html + "</tbody></table>" if rounds_history else '<div class="empty">No rounds played yet</div>'}
</body>
</html>"""


def generate_round_detail_html(round_data):
    """Generate individual round detail page with visual Plinko board."""
    r = round_data
    rows = r['rows']
    outcome = r['outcome']
    risk = r['risk_level']
    multipliers = PAYTABLE[str(rows)][risk]

    # Build the visual Plinko board
    # Ball starts at center, each step goes left (0) or right (1)
    # Position tracks horizontal offset from leftmost possible position
    board_lines = []
    ball_col = 0  # ball position: 0=leftmost at each row

    for row_idx in range(rows):
        num_pins = row_idx + 3  # row 0 has 3 pins, row 1 has 4, etc.
        pin_spacing = 4
        total_width = (rows + 2) * pin_spacing
        offset = (rows - row_idx) * (pin_spacing // 2)

        # Build pin row
        line = ""
        for pin in range(num_pins):
            pos = offset + pin * pin_spacing
            line += " " * (pos - len(line))
            if pin == ball_col or pin == ball_col + 1:
                # This pin is adjacent to ball path
                line += "\u25cf" if (pin == ball_col and row_idx > 0) else "\u25cb"
            else:
                line += "\u25cb"

        board_lines.append(line)

        # Arrow row showing ball direction
        if row_idx < len(outcome):
            direction = outcome[row_idx]
            arrow_pos = offset + ball_col * pin_spacing + (pin_spacing // 2)
            if direction == 1:
                arrow_line = " " * arrow_pos + "\u2198"  # down-right
                ball_col += 1
            else:
                arrow_line = " " * (arrow_pos - 1) + "\u2199\ufe0e"  # down-left
            board_lines.append(arrow_line)

    # Build multiplier row
    mult_strs = [f"x{int(m)}" if m == int(m) else f"x{m}" for m in multipliers]
    bucket = r['bucket']

    # Header info
    bet_display = f"{r['bet']/100:.2f}"
    win_display = f"{r['win']/100:.2f}"
    profit_val = r['profit'] / 100
    profit_display = f"{profit_val:+.2f}" if profit_val != 0 else "0.00"
    bal_before = f"{r['balance_before']/100:.2f}"
    bal_after = f"{r['balance_after']/100:.2f}"

    # Multiplier cells
    mult_cells = ""
    for i, m in enumerate(mult_strs):
        cls = ' class="active"' if i == bucket else ""
        mult_cells += f"<span{cls}>{m}</span> "

    board_text = "\n".join(board_lines)

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>Plinko: Round #{r['id']}</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ font-family: "Courier New", Consolas, monospace; background: #1a1a2e; color: #e0e0e0; padding: 20px; }}
  h1 {{ text-align: center; margin-bottom: 20px; font-size: 20px; color: #fff; }}
  .back {{ display: inline-block; margin-bottom: 16px; color: #e94560; text-decoration: none; font-size: 14px; }}
  .back:hover {{ text-decoration: underline; }}
  .info {{ max-width: 600px; margin: 0 auto 24px; }}
  .info-row {{ display: flex; justify-content: space-between; padding: 6px 0; border-bottom: 1px solid #16213e; font-size: 14px; }}
  .info-row .label {{ color: #888; }}
  .info-row .value {{ color: #fff; }}
  .board {{ text-align: center; margin: 24px auto; padding: 20px; background: #16213e; border-radius: 8px; max-width: 700px; overflow-x: auto; }}
  .board pre {{ font-size: 14px; line-height: 1.6; color: #aaa; display: inline-block; text-align: left; }}
  .multipliers {{ text-align: center; margin: 16px auto; max-width: 700px; }}
  .multipliers span {{ display: inline-block; padding: 4px 8px; margin: 2px; font-size: 12px; background: #16213e; border-radius: 4px; color: #888; }}
  .multipliers span.active {{ background: #e94560; color: #fff; font-weight: bold; }}
  .bet-win {{ text-align: center; margin: 16px 0; font-size: 16px; }}
  .bet-win .bet {{ color: #aaa; }}
  .bet-win .win {{ color: #4ecca3; font-weight: bold; }}
</style>
</head>
<body>
<a class="back" href="/api/rounds_history/offline">&larr; Back to History</a>
<h1>Plinko: Round #{r['id']}</h1>
<div class="info">
  <div class="info-row"><span class="label">Date/Time</span><span class="value">{r['timestamp']} UTC+00:00</span></div>
  <div class="info-row"><span class="label">Bet</span><span class="value">{r['bet']}</span></div>
  <div class="info-row"><span class="label">Total Win</span><span class="value">{r['win']}</span></div>
  <div class="info-row"><span class="label">Profit</span><span class="value">{profit_display}</span></div>
  <div class="info-row"><span class="label">Balance Before</span><span class="value">{bal_before}</span></div>
  <div class="info-row"><span class="label">Balance after</span><span class="value">{bal_after}</span></div>
  <div class="info-row"><span class="label">Currency</span><span class="value">{r['currency']}</span></div>
  <div class="info-row"><span class="label">Used Feature</span><span class="value">No</span></div>
</div>
<div class="bet-win"><span class="bet">Bet: {r['bet']}</span></div>
<div class="board"><pre>{board_text}</pre></div>
<div class="multipliers">{mult_cells}</div>
<div class="bet-win"><span class="win">Win: {r['win']}</span></div>
</body>
</html>"""


# ═══════════════════════════════════════════════════════
# HTTP SERVER
# ═══════════════════════════════════════════════════════

MIME_OVERRIDES = {
    '.js': 'application/javascript; charset=utf-8',
    '.html': 'text/html; charset=utf-8',
    '.json': 'application/json; charset=utf-8',
    '.css': 'text/css; charset=utf-8',
}


class PlinkoHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', '*')
        super().end_headers()

    def guess_type(self, path):
        ext = os.path.splitext(path)[1].lower()
        if ext in MIME_OVERRIDES:
            return MIME_OVERRIDES[ext]
        return super().guess_type(path)

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def _send_json(self, data):
        response_bytes = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', len(response_bytes))
        self.end_headers()
        self.wfile.write(response_bytes)

    def do_POST(self):
        path = self.path

        # === GAME API ===
        if '/api/Plinko/' in path or '/api/games/verify' in path:
            content_length = int(self.headers.get('Content-Length', 0))
            body_bytes = self.rfile.read(content_length) if content_length > 0 else b'{}'
            try:
                body = json.loads(body_bytes)
            except json.JSONDecodeError:
                body = {}

            if '/verify' in path:
                print(f"  [VERIFY] secret={body.get('secret','')[:60]}...")
                response_data = handle_verify(body)
                print(f"  [VERIFY] hash={response_data['hash']}")
            elif body.get("command") == "init":
                response_data = handle_init()
                print(f"  [INIT] hash={response_data['extra_data']['provable_data'][0]['hash'][:20]}...")
            elif body.get("command") == "play":
                response_data = handle_play(
                    body.get("options", {}),
                    body.get("extra_data", {})
                )
                if "errors" in response_data:
                    print(f"  [PLAY] ERROR: insufficient balance ({response_data['balance']})")
                else:
                    pd = response_data['extra_data']['provable_data']
                    print(f"  [PLAY] seed={body.get('extra_data',{}).get('client_seed','?')} win={response_data['result']} bal={response_data['balance']}")
                    print(f"  [PLAY] revealed_hash={pd[1]['hash'][:20]}... next_hash={pd[0]['hash'][:20]}...")
            elif body.get("command") == "close_session":
                response_data = {"success": True}
            else:
                response_data = handle_init()

            self._send_json(response_data)
            return

        # === ROUNDS HISTORY ===
        if '/api/rounds_history/' in path:
            self._send_json({"rounds": []})
            return

        self.do_GET()

    def do_GET(self):
        path = self.path.split('?')[0].lstrip('/')

        # === Individual Round Detail page ===
        if path.startswith('api/rounds_history/-/'):
            round_id_str = path.split('/')[-1]
            try:
                round_id = int(round_id_str)
            except ValueError:
                round_id = None
            round_data = None
            if round_id is not None:
                for r in rounds_history:
                    if r['id'] == round_id:
                        round_data = r
                        break
            if round_data:
                html = generate_round_detail_html(round_data)
                print(f"  [HISTORY] Served round detail #{round_id}")
            else:
                html = "<html><body><h1>Round not found</h1></body></html>"
            html_bytes = html.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(html_bytes))
            self.end_headers()
            self.wfile.write(html_bytes)
            return

        # === Rounds History list page ===
        if path.startswith('api/rounds_history/'):
            html = generate_history_html()
            html_bytes = html.encode('utf-8')
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', len(html_bytes))
            self.end_headers()
            self.wfile.write(html_bytes)
            print(f"  [HISTORY] Served history page ({len(rounds_history)} rounds)")
            return

        # === Serve local files first ===
        local_path = self.translate_path(self.path)
        if os.path.isfile(local_path):
            return super().do_GET()

        # === CDN Proxy + Cache ===
        cdn_url = None
        cache_path = None

        if path.startswith('assets/'):
            cdn_path = path[len('assets/'):]
            cdn_url = f"{CDN_BASE}/{cdn_path}"
            cache_path = os.path.join(os.getcwd(), path)
        elif path.startswith('games-aux/'):
            cdn_url = f"https://cdn.bgaming-network.com/{path}"
            cache_path = os.path.join(os.getcwd(), path)

        if cdn_url and cache_path:
            try:
                req = urllib.request.Request(cdn_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    ctype = resp.headers.get('Content-Type', 'application/octet-stream')
                    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
                    with open(cache_path, 'wb') as f:
                        f.write(data)
                    print(f"  [CDN] cached {path} ({len(data)} bytes)")
                    self.send_response(200)
                    self.send_header('Content-Type', ctype)
                    self.send_header('Content-Length', len(data))
                    self.end_headers()
                    self.wfile.write(data)
                    return
            except Exception as e:
                print(f"  [CDN-FAIL] {path}: {e}")

        return super().do_GET()

    def log_message(self, format, *args):
        msg = format % args
        if '404' in msg:
            print(f"  [MISS] {msg}")


print(f"""
====================================================
  PLINKO OFFLINE - FULL SERVER
====================================================
  URL:     http://localhost:{PORT}
  Balance: {game_balance/100:.2f} FUN
  Provably Fair: SHA-256 + Rotation
  CDN Cache: Auto-fetch and store locally
====================================================
""")

with http.server.HTTPServer(("", PORT), PlinkoHandler) as httpd:
    httpd.serve_forever()

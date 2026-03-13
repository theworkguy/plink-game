# Provably Fair Algorithm Specification

Complete specification of the cryptographic provably fair system. This is the exact same algorithm used by BGaming — verified against their live API with hash-for-hash matching.

## Overview

The provably fair system ensures neither the server nor the player can manipulate the game outcome after commitment. It uses:

1. **SHA-256 hash commitment** — server commits to an outcome before the player acts
2. **Array rotation by client seed** — player influences the result without the server being able to predict it
3. **Post-game reveal** — server reveals the secret, player verifies the hash matches

## Algorithm Step-by-Step

### Before the Game (Server Commitment)

```
1. Generate 32 random bits: outcome = [1,0,1,1,0,...] (32 values, each 0 or 1)
2. Generate random hex secret: secret = "926825cfd3efb8da4adc79ba67538acd"
3. Create JSON (compact, no spaces):
   secret_json = {"outcome":[1,0,1,1,0,...],"game":"Plinko","secret":"926825cfd3efb8da4adc79ba67538acd"}
4. Compute hash: SHA256(secret_json) = "a38212a3f880ff2c..."
5. Show hash to player BEFORE they click Play
```

### During the Game (Player Input)

```
6. Player provides client_seed (any integer, e.g. 42)
7. Player clicks Play
```

### After the Game (Result Calculation)

```
8. rotation = int(client_seed) % 32
9. rotated_outcome = outcome[rotation:] + outcome[:rotation]
10. game_result = rotated_outcome[0:rows]  (first N values, where N = selected rows)
11. bucket_index = sum(game_result)  (count of 1s)
12. multiplier = paytable[rows][risk_level][bucket_index]
13. win = int(bet * multiplier + 0.5)
```

### After the Game (Reveal & Verify)

```
14. Server reveals: secret_json (the full JSON from step 3)
15. Player computes: SHA256(secret_json)
16. Player checks: computed_hash == hash_shown_in_step_5
17. If match: the game was fair — the outcome was determined before the player acted
```

## Why This Is Provably Fair

- The server commits to the outcome (via hash) BEFORE the player provides their seed
- The server cannot change the outcome after commitment (would change the hash)
- The player's seed rotates the array, so the server cannot predict which portion will be used
- After the game, the player can independently verify the hash matches the revealed secret
- SHA-256 is a one-way function — the server cannot find a different secret that produces the same hash

## Code Examples

### Python — Generate and Verify

```python
import hashlib
import json
import secrets

# === SERVER SIDE: Generate seed ===
outcome = [secrets.randbelow(2) for _ in range(32)]
secret_hex = secrets.token_hex(16)

seed_data = {
    "outcome": outcome,
    "game": "Plinko",
    "secret": secret_hex
}

# CRITICAL: Use compact JSON with no spaces (matches BGaming format)
seed_json = json.dumps(seed_data, separators=(',', ':'))
seed_hash = hashlib.sha256(seed_json.encode()).hexdigest()

# Show seed_hash to player before they play
print(f"Pre-game hash: {seed_hash}")

# === PLAYER PLAYS ===
client_seed = 42
rows = 12

# === SERVER SIDE: Calculate result ===
rotation = client_seed % 32
rotated = outcome[rotation:] + outcome[:rotation]
game_outcome = rotated[:rows]
bucket = sum(game_outcome)

# === SERVER SIDE: Reveal ===
print(f"Revealed secret: {seed_json}")

# === CLIENT SIDE: Verify ===
verify_hash = hashlib.sha256(seed_json.encode()).hexdigest()
print(f"Verified: {verify_hash == seed_hash}")  # Must be True
```

### JavaScript — Client-Side Verification

```javascript
async function verifyRound(preGameHash, revealedSecret) {
    // Compute SHA-256 of the revealed secret
    const encoder = new TextEncoder();
    const data = encoder.encode(revealedSecret);
    const hashBuffer = await crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const computedHash = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');

    // Compare with the hash shown before the round
    const isValid = computedHash === preGameHash;
    console.log(`Verification: ${isValid ? 'PASSED' : 'FAILED'}`);
    return isValid;
}

function replayOutcome(revealedSecret, clientSeed, rows) {
    const data = JSON.parse(revealedSecret);
    const outcome = data.outcome;  // 32-bit array
    const rotation = clientSeed % 32;
    const rotated = [...outcome.slice(rotation), ...outcome.slice(0, rotation)];
    const gameResult = rotated.slice(0, rows);
    const bucket = gameResult.reduce((a, b) => a + b, 0);
    return { gameResult, bucket };
}
```

### cURL — Manual Verification

```bash
# 1. Init game and get the pre-game hash
INIT=$(curl -s -X POST http://localhost:8080/api/Plinko/0/offline \
  -H "Content-Type: application/json" \
  -d '{"command":"init"}')
HASH=$(echo $INIT | python3 -c "import sys,json; print(json.load(sys.stdin)['extra_data']['provable_data'][0]['hash'])")
echo "Pre-game hash: $HASH"

# 2. Play a round
PLAY=$(curl -s -X POST http://localhost:8080/api/Plinko/0/offline \
  -H "Content-Type: application/json" \
  -d '{"command":"play","options":{"bet":100,"risk_level":"medium","rows":12},"extra_data":{"client_seed":42}}')
SECRET=$(echo $PLAY | python3 -c "import sys,json; print(json.load(sys.stdin)['extra_data']['provable_data'][1]['secret'])")
echo "Revealed secret: $SECRET"

# 3. Verify: SHA256 of revealed secret must match pre-game hash
COMPUTED=$(echo -n "$SECRET" | sha256sum | cut -d' ' -f1)
echo "Computed hash:   $COMPUTED"
echo "Pre-game hash:   $HASH"
echo "Match: $([ "$COMPUTED" = "$HASH" ] && echo YES || echo NO)"
```

## Secret JSON Format

The JSON format is critical — it must be compact with no spaces:

```
{"outcome":[1,0,1,1,0,0,1,0,1,1,0,0,0,0,1,1,1,1,0,1,1,0,0,0,0,0,1,0,1,1,1,0],"game":"Plinko","secret":"926825cfd3efb8da4adc79ba67538acd"}
```

Key rules:
- Separator: `,` between items, `:` between key/value — NO spaces
- Field order: `outcome`, `game`, `secret` (Python `json.dumps` default order)
- `outcome` is always 32 integers, each `0` or `1`
- `game` is always `"Plinko"`
- `secret` is always 32 hex characters (16 bytes)

## Rotation Example

```
Server outcome: [A,B,C,D,E,F,G,H,I,J,...] (32 values)
Client seed: 42
Rotation: 42 % 32 = 10

Rotated: [K,L,M,...,Z,A,B,C,D,E,F,G,H,I,J]
         (elements 10-31, then elements 0-9)

If rows = 8: game_result = first 8 values of rotated array
Bucket = count of 1s in game_result
```

## Security Properties

| Property | Guarantee |
|----------|-----------|
| Pre-commitment | Server cannot change outcome after showing hash |
| Player influence | Client seed rotation prevents server from choosing which bits are used |
| Verifiability | Anyone can recompute SHA-256 and verify the hash matches |
| Uniqueness | Each round has a unique 32-byte secret, making hash collisions infeasible |
| Randomness | `secrets.randbelow()` uses OS-level CSPRNG (cryptographically secure) |

## RTP (Return to Player)

The paytable is mathematically verified:

| Risk Level | RTP Range |
|------------|-----------|
| Main | 98.91% |
| Minimum | 98.91% |
| Maximum | 99.16% |

Maximum single-round multiplier: **x1000** (16 rows, high risk, all bits same direction)

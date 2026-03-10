# Bonus Microservice

## Description
The Bonus Microservice evaluates whether a spin **triggers a bonus** based on a configurable rule and returns which grid symbols caused it. It supports a simple *scatter count* trigger type and an optional probability gate, with deterministic behavior when a `seed` is provided.

If no `gameId` concept is needed, you can call this service directly with the grid and bonus configuration.

---

# Endpoints

# 1. Health Check
GET /healthz

Used to verify that the microservice is running.

Example Request:
GET /healthz

Example Response:
```
{
  "status": "ok",
  "service": "bonus",
  "version": "0.1.0"
}
```

---

# 2. Ping (Echo)
POST /ping

Connectivity test; echoes any JSON you send.

Example Request:
POST /ping

Body:
```
{ "hello": "world" }
```

Example Response:
```
{ "pong": true, "echo": { "hello": "world" } }
```

---

# 3. Evaluate Bonus
POST /bonus/evaluate

Evaluates a spin grid against a *scatter count* configuration. Triggers when the specified symbol appears at least `count` times anywhere on the grid. Optionally applies a probability gate `prob` in [0,1]. When `seed` is supplied, the probability decision is deterministic for the same inputs.

Example Request:
POST /bonus/evaluate

Body:
```
{
  "grid": [["A","B","S"],["S","S","C"],["D","E","F"]],
  "config": {
    "type": "scatter_count",
    "symbol": "S",
    "count": 3,
    "prob": 0.75
  },
  "seed": 20260310
}
```

Example Response (triggered):
```
{
  "bonusTriggered": true,
  "highlights": [{"r":0,"c":2},{"r":1,"c":0},{"r":1,"c":1}],
  "type": "scatter_count",
  "symbol": "S",
  "threshold": 3,
  "count": 3
}
```

Error Example (invalid grid):
```
{
  "detail": "grid must be non-empty 2D array"
}
```

---

# Communication Contract

# Requesting Data
To request data from the Bonus Microservice:

1. Send an HTTP `POST` request to `/bonus/evaluate`.
2. Include a JSON body with:
   - `grid`: a non-empty 2D array of symbol strings; all rows must be equal length.
   - `config`: `{ "type":"scatter_count", "symbol": <str>, "count": <int>=3, "prob": <float in [0,1]> }`.
   - `seed` *(optional int)* to make probability decision deterministic for testing.

Example (Python):
```python
import requests

payload = {
    "grid": [["A","B","S"],["S","S","C"],["D","E","F"]],
    "config": {"type":"scatter_count", "symbol":"S", "count":3, "prob":0.75},
    "seed": 20260310
}
resp = requests.post("http://127.0.0.1:8095/bonus/evaluate", json=payload)
print(resp.json())
```

---

# Receiving Data
The microservice responds with JSON data.

Example response format:
```
{
  "bonusTriggered": <bool>,
  "highlights": [{"r": <row>, "c": <col>}, ...],
  "type": "scatter_count",
  "symbol": "S",
  "threshold": 3,
  "count": <int>
}
```

Example handling in Python:
```python
data = resp.json()
if data["bonusTriggered"]:
    coords = [(h["r"], h["c"]) for h in data["highlights"]]
    print("Bonus! Matching positions:", coords)
else:
    print("No bonus this spin.")
```

---

# UML Sequence Diagram
```
Main Program        Bonus Microservice
     |                      |
     |---- POST /bonus/evaluate ------------------------->|
     |                      |---- Count scatter symbols -->|
     |                      |---- Prob gate (if prob<1) -->|
     |                      |<--- JSON {bonusTriggered} ---|
     |<--- JSON Response ---|                              |
```

---

# How to Run the Microservice

1. Install dependencies:
```
pip install fastapi uvicorn pydantic
```

2. Start the server:
```
uvicorn bonus_service:app --reload --port 8095
```
*(If your file/module is named differently, adjust the module path accordingly. The provided implementation uses `bonus_service:app` in its run notes.)*

3. Open in browser:
```
http://127.0.0.1:8095/docs
```

---

# Test Program Example
```python
import requests

BASE = "http://127.0.0.1:8095"

# Example grid with three S symbols (meets threshold=3)
payload = {
    "grid": [["A","B","S"],["S","S","C"],["D","E","F"]],
    "config": {"type":"scatter_count", "symbol":"S", "count":3, "prob":1.0}
}

r = requests.post(f"{BASE}/bonus/evaluate", json=payload)
print("Evaluate (prob=1.0):", r.json())

# With probability gate and seed (deterministic)
payload["config"]["prob"] = 0.5
payload["seed"] = 424242
r = requests.post(f"{BASE}/bonus/evaluate", json=payload)
print("Evaluate (prob=0.5, seed=424242):", r.json())
```

---

## Notes
- All communication is JSON over HTTP.
- Grid must be a non-empty rectangle (equal-length rows).
- `scatter_count` triggers when occurrences ≥ `count`; if `prob` < 1, a probability gate is applied.
- Determinism: when `seed` is provided, a stable hash of `(grid + config)` is combined with `seed` to seed RNG for the probability check.
- Service exposes `/healthz`, `/ping`, and `/bonus/evaluate`; interactive docs at `/docs`.

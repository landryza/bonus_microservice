# bonus_service.py
"""
Bonus Microservice

Purpose:
- Decide whether a spin triggers a free‑spin bonus and return which symbols caused it.

Features:
- GET  /healthz
- POST /ping
- POST /bonus/evaluate
- Swagger UI at /docs

Trigger model:
- type = "scatter_count" → trigger when a specific symbol appears at least N times anywhere on the grid.
- Optional probability gate prob in [0,1]. Determinism uses (seed + stable hash of grid+config).

Run (Windows PowerShell):
  cd <folder>
  python -m venv .venv
  . .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  pip install fastapi uvicorn pydantic
  python -m uvicorn bonus_service:app --host 127.0.0.1 --port 8095 --reload
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, conint, confloat
from typing import List, Optional, Literal, Dict
import hashlib, json, random

app = FastAPI(title="Bonus Microservice (Minimal)", version="0.1.0")

class ScatterConfig(BaseModel):
    type: Literal["scatter_count"] = "scatter_count"
    symbol: str = Field(...)
    count: conint(ge=1) = Field(3)
    prob: Optional[confloat(ge=0, le=1)] = Field(1.0)

class EvaluateRequest(BaseModel):
    grid: List[List[str]]
    config: ScatterConfig
    seed: Optional[int] = None

class Highlight(BaseModel):
    r: int
    c: int

class EvaluateResponse(BaseModel):
    bonusTriggered: bool
    highlights: List[Highlight]
    type: str
    symbol: str
    threshold: int
    count: int

def _stable_int_from_payload(payload: Dict, seed: Optional[int]) -> int:
    blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    h = hashlib.sha256(blob).digest()
    base = int.from_bytes(h[:8], "big")
    if seed is not None:
        base ^= (seed & ((1<<63)-1))
    return base

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "bonus", "version": app.version}

@app.post("/ping")
def ping(msg: Optional[dict] = None):
    return {"pong": True, "echo": msg or {}}

@app.post("/bonus/evaluate", response_model=EvaluateResponse)
def evaluate(body: EvaluateRequest):
    grid = body.grid
    if not grid or not grid[0]:
        raise HTTPException(status_code=400, detail="grid must be non-empty 2D array")

    sym = body.config.symbol
    threshold = int(body.config.count)
    highlights = []
    rows = len(grid)
    cols = len(grid[0])
    for r in range(rows):
        if len(grid[r]) != cols:
            raise HTTPException(status_code=400, detail="all grid rows must have equal length")
        for c in range(cols):
            if grid[r][c] == sym:
                highlights.append({"r": r, "c": c})

    cnt = len(highlights)
    triggered = False
    if cnt >= threshold:
        prob = 1.0 if body.config.prob is None else float(body.config.prob)
        if prob >= 1.0:
            triggered = True
        elif prob <= 0.0:
            triggered = False
        else:
            base = _stable_int_from_payload({"grid": grid, "config": body.config.model_dump()}, body.seed)
            rng = random.Random(base)
            triggered = (rng.random() < prob)

    out_highlights = highlights if triggered else []
    return {
        "bonusTriggered": triggered,
        "highlights": out_highlights,
        "type": body.config.type,
        "symbol": sym,
        "threshold": threshold,
        "count": cnt,
    }

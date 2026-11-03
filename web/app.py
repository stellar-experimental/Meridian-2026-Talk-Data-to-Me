"""Talk Data to Me, web demo: ask a fee question, Claude answers through Malloy.

Claude gets exactly one tool, run_malloy. There is no SQL tool, so the gate
the repo README says is missing is enforced here, outside the model.

    uvicorn app:app --port 8080            (from web/)

Model access: ANTHROPIC_API_KEY if set, otherwise Claude on Vertex AI in
GOOGLE_CLOUD_PROJECT.
"""
import asyncio
import json
import os
import threading
import time
from collections import defaultdict, deque
from pathlib import Path

import anthropic
import duckdb
import malloy
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from malloy.data.duckdb import DuckDbConnection
from pydantic import BaseModel, Field

HERE = Path(__file__).parent
MODEL_FILE = HERE / "fees_daily.malloy"
DB_FILE = HERE / "operations.duckdb"
MAX_TURNS = 6
MAX_ROWS = 100
QUERY_TIMEOUT_S = 5
# Questions per IP per window (seconds). Conference Wi-Fi puts a whole room
# behind one NAT address, so the per-IP budget has to cover an audience.
RATE_LIMIT = (int(os.environ.get("RATE_LIMIT_QUESTIONS", 100)),
              int(os.environ.get("RATE_LIMIT_WINDOW_S", 300)))

# Read-only database, no file system or network, settings frozen. A query can
# only see operations_daily, however it is written.
_db = duckdb.connect(str(DB_FILE), read_only=True)
for stmt in ("SET memory_limit='1GB'", "SET threads=2",
             "SET enable_external_access=false", "SET lock_configuration=true"):
    _db.execute(stmt)


class LockedDuckDb(DuckDbConnection):
    def get_connection(self):
        return _db.cursor()

    def set_home_dir(self, path):
        pass  # SET FILE_SEARCH_PATH would fail on the locked config


_malloy = malloy.Runtime()
_malloy.add_connection(LockedDuckDb())
_malloy.load_file(str(MODEL_FILE))
# ponytail: one compile at a time (Runtime keeps per-call state); queries take
# milliseconds on this table, a Runtime pool if it ever queues.
_malloy_lock = asyncio.Lock()


def _execute(sql: str) -> list[dict]:
    cur = _db.cursor()
    timer = threading.Timer(QUERY_TIMEOUT_S, cur.interrupt)
    timer.start()
    try:
        cur.execute(sql)
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, r)) for r in cur.fetchmany(MAX_ROWS)]
    finally:
        timer.cancel()


async def run_malloy(query: str) -> dict:
    q = query.strip()
    if not q.startswith("run: operations") or "duckdb" in q or "import" in q:
        return {"error": "Only `run: operations -> ...` queries on the model are allowed."}
    async with _malloy_lock:
        try:
            sql, _ = await _malloy.get_sql(query=q)
            rows = await asyncio.to_thread(_execute, sql)
        except Exception as e:  # compile or runtime error goes back to the model
            return {"error": str(e).splitlines()[0][:500]}
    return {"rows": rows, "sql": sql}


SYSTEM = f"""You answer questions about Stellar network fees for people at a \
conference, who are reading on their phones.

The only data you can use is the Malloy model below. Your only tool is \
run_malloy, which runs one Malloy query against it. You cannot write SQL.

How to answer:
1. Pick the measure or view in the model that answers the question: fees_xlm, \
txn_count, op_count, fee_per_txn_xlm, or the views daily_fees, monthly_fees, \
fees_by_type. Use them by name; never write inline aggregates such as \
sum(fee_charged).
2. Call run_malloy with a query in one of these shapes (the date range end is \
exclusive):
   run: operations -> {{ where: close_day = @2026-08-15; aggregate: fees_xlm, txn_count }}
   run: operations -> {{ where: close_day ? @2026-08; aggregate: fees_xlm }}
   run: operations -> {{ where: close_day ? @2026-Q2; aggregate: fees_xlm }}
   run: operations -> {{ where: close_day ? @2026-08-24 to @2026-09-01; aggregate: txn_count }}
   run: operations -> daily_fees + {{ where: close_day ? @2026-08-01 to @2026-08-08 }}
   run: operations -> fees_by_type + {{ where: close_day ? @2026-09; limit: 5 }}
   run: operations -> monthly_fees
   To filter a view, write `view_name + {{ where: ... }}`; nothing else.
   For any total (a day, month, quarter or range), return ONE row with an \
aggregate query like the second and third examples. Never add up rows \
yourself. Always filter on close_day, never close_month. Quarters are \
close_day ? @2026-Q2 (Q2 = Apr-Jun). Use daily_fees or monthly_fees only when \
the question asks for a breakdown or a comparison between periods.
3. Answer in two or three short sentences of plain text, no markdown: the \
number (rounded sensibly, with units), then which measure you used and why it \
is right, quoting its # comment in a few words.

Data covers 2025-10-01 through 2026-09-30, by day; there is nothing finer \
than a day. Fees are in XLM as the query returns them; do not convert units \
yourself. There is no USD price. If the model cannot answer \
a question, say so plainly and do not guess or answer from memory. If a \
question is not about this data, say what you can answer instead.

<malloy_model>
{MODEL_FILE.read_text()}
</malloy_model>"""

TOOLS = [{
    "name": "run_malloy",
    "description": "Run one Malloy query against the fees model and return up "
                   f"to {MAX_ROWS} rows plus the SQL Malloy generated.",
    "input_schema": {
        "type": "object",
        "properties": {"query": {"type": "string", "description": "A Malloy query starting with `run: operations ->`."}},
        "required": ["query"],
        "additionalProperties": False,
    },
}]

# Haiku 4.5: the cheapest Claude, and enough for "pick a measure, run one query".
if os.environ.get("ANTHROPIC_API_KEY"):
    _claude = anthropic.AsyncAnthropic()
    MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5")
else:
    _claude = anthropic.AsyncAnthropicVertex(project_id=os.environ["GOOGLE_CLOUD_PROJECT"], region="global")
    MODEL = os.environ.get("CLAUDE_MODEL", "claude-haiku-4-5@20251001")


async def answer(question: str) -> dict:
    messages = [{"role": "user", "content": question}]
    queries = []
    for _ in range(MAX_TURNS):
        resp = await _claude.messages.create(
            model=MODEL, max_tokens=2000, system=SYSTEM, tools=TOOLS, messages=messages,
        )
        if resp.stop_reason == "refusal":
            return {"answer": "I can't help with that one. Try a question about Stellar fees.", "queries": queries}
        if resp.stop_reason != "tool_use":
            text = "".join(b.text for b in resp.content if b.type == "text").strip()
            return {"answer": text, "queries": queries}
        messages.append({"role": "assistant", "content": resp.content})
        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            out = await run_malloy(b.input.get("query", ""))
            queries.append({"malloy": b.input.get("query", ""), **out})
            results.append({"type": "tool_result", "tool_use_id": b.id,
                            "content": json.dumps(out, default=str), "is_error": "error" in out})
        messages.append({"role": "user", "content": results})
    return {"answer": "That took too many steps. Try a simpler question.", "queries": queries}


app = FastAPI()
_hits: dict[str, deque] = defaultdict(deque)


class Ask(BaseModel):
    question: str = Field(min_length=1, max_length=500)


@app.get("/")
def index():
    return FileResponse(HERE / "index.html")


@app.post("/api/ask")
async def ask(body: Ask, request: Request):
    # Cloud Run puts the client first in X-Forwarded-For.
    ip = request.headers.get("x-forwarded-for", request.client.host).split(",")[0].strip()
    now, (limit, window) = time.time(), RATE_LIMIT
    hits = _hits[ip]
    while hits and hits[0] < now - window:
        hits.popleft()
    if len(hits) >= limit:
        raise HTTPException(429, "Too many questions. Give it a few minutes.")
    hits.append(now)
    try:
        return await answer(body.question)
    except anthropic.APIError as e:
        raise HTTPException(503, f"The model is unavailable right now ({type(e).__name__}).")

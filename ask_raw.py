"""Ask the same fee question. Claude answers with RAW SQL on the warehouse.

The model gets one tool, run_sql, and a schema: table name, column names,
column types. Nothing else. This is what "point an LLM at the warehouse"
looks like, and it is the contrast case for ask.py.

    export ANTHROPIC_API_KEY=...
    python ask_raw.py "what were network fees on June 15 2026?"
"""
import json
import os
import sys

import anthropic
from anthropic import beta_tool
from google.cloud import bigquery

TABLE = "crypto-stellar.crypto_stellar_dbt.enriched_history_operations"
MAX_BYTES = int(os.environ.get("BQ_MAX_BYTES", 2_000_000_000_000))  # 2 TB guard

# Names and types only. This is all INFORMATION_SCHEMA gives you.
SCHEMA = """
op_id                INT64
transaction_hash     STRING
transaction_id       INT64
type_string          STRING
closed_at            TIMESTAMP
successful           BOOL
fee_charged          INT64
max_fee              INT64
txn_operation_count  INT64
source_account       STRING
"""


@beta_tool
def run_sql(sql: str) -> str:
    """Run a BigQuery SQL query and return the rows.

    Args:
        sql: Standard SQL. Filter closed_at to a short range; the table is large.
    """
    client = bigquery.Client()
    cfg = bigquery.QueryJobConfig(maximum_bytes_billed=MAX_BYTES)
    try:
        rows = [dict(r) for r in client.query(sql, job_config=cfg).result()]
    except Exception as e:
        return json.dumps({"error": str(e)[:2000]})
    return json.dumps({"rows": rows}, default=str)


SYSTEM = f"""You are a data analyst answering questions about the Stellar network.
You have one tool, run_sql, which runs BigQuery Standard SQL.

Table: `{TABLE}`
Columns:
{SCHEMA}
Always filter closed_at to a short range. Answer with the number and the query you ran.
"""


def main(question: str) -> None:
    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model="claude-sonnet-5",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        tools=[run_sql],
        messages=[{"role": "user", "content": question}],
    )
    for message in runner:
        for block in message.content:
            if block.type == "tool_use":
                print("\n[run_sql]")
                print(block.input["sql"])
            elif block.type == "text" and block.text.strip():
                print("\n" + block.text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "What were total network fees on June 15, 2026?")

"""Run one Malloy query against fees.malloy on BigQuery. No LLM involved.

    .venv/bin/python run_malloy.py "run: operations -> { where: closed_at ? @2026-08-15; aggregate: fees_xlm }"

Prints the rows as JSON, then the SQL Malloy generated. Needs
`gcloud auth application-default login` and a billing project.
"""
import asyncio
import json
import sys
from pathlib import Path

import malloy
from malloy.data.bigquery import BigQueryConnection

MODEL_FILE = Path(__file__).parent / "fees.malloy"


async def run(query: str) -> tuple[list[dict], str]:
    with malloy.Runtime() as rt:
        rt.add_connection(BigQueryConnection())
        rt.load_file(str(MODEL_FILE))
        result, sql, _ = await rt.get_sql_and_run(query=query)
        rows = [dict(r) for r in result.result()]
    return rows, sql


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    rows, sql = asyncio.run(run(sys.argv[1]))
    print(json.dumps(rows, default=str, indent=2))
    print("\n-- generated SQL --")
    print(sql)


if __name__ == "__main__":
    main()

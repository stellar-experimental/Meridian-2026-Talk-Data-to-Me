"""Ask a fee question. Claude answers THROUGH the semantic layer.

The model gets one tool, run_malloy, which compiles a Malloy query against
fees.malloy and executes it on BigQuery. There is no SQL tool. The model
picks measures; Malloy writes the SQL.

    export ANTHROPIC_API_KEY=...
    python ask.py "what were network fees on June 15 2026?"
"""
import asyncio
import json
import sys
from pathlib import Path

import anthropic
from anthropic import beta_tool
import malloy
from malloy.data.bigquery import BigQueryConnection

MODEL_FILE = Path(__file__).parent / "fees.malloy"
MODEL_TEXT = MODEL_FILE.read_text()


async def _run(query: str) -> dict:
    with malloy.Runtime() as rt:
        rt.add_connection(BigQueryConnection())
        rt.load_file(str(MODEL_FILE))
        result, sql, _ = await rt.get_sql_and_run(query=query)
        rows = [dict(r) for r in result.result()]
    return {"rows": rows, "sql": sql}


@beta_tool
def run_malloy(query: str) -> str:
    """Run a Malloy query against the semantic model in fees.malloy.

    Args:
        query: A Malloy `run:` statement using the `operations` source, its
            measures (fees_xlm, txn_count, op_count, fee_per_txn_xlm) and
            views (daily_fees, fees_by_type). Always include a `where:` on
            closed_at. Example:
            run: operations -> { where: closed_at ? @2026-06-15; aggregate: fees_xlm }
    """
    try:
        out = asyncio.run(_run(query))
    except Exception as e:  # surface compile/runtime errors to the model
        return json.dumps({"error": str(e)[:2000]})
    return json.dumps(out, default=str)


SYSTEM = f"""You are a data analyst answering questions about the Stellar network.

You have ONE tool, run_malloy, which runs a Malloy query against the semantic
model below. You cannot write SQL. Pick measures and views defined in the model;
never write inline aggregates such as sum(fee_charged). Always include a date
filter on closed_at. When you answer, state which measure you used and quote its
comment from the model.

<model file="fees.malloy">
{MODEL_TEXT}
</model>
"""


def main(question: str) -> None:
    client = anthropic.Anthropic()
    runner = client.beta.messages.tool_runner(
        model="claude-sonnet-5",
        max_tokens=16000,
        thinking={"type": "adaptive"},
        system=SYSTEM,
        tools=[run_malloy],
        messages=[{"role": "user", "content": question}],
    )
    for message in runner:
        for block in message.content:
            if block.type == "tool_use":
                print("\n[run_malloy]")
                print(block.input["query"])
            elif block.type == "text" and block.text.strip():
                print("\n" + block.text)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "What were total network fees on June 15, 2026?")

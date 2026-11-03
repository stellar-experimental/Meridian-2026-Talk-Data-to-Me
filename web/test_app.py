"""Self-check for the tool gate and the measures. No model calls.

    cd web && GOOGLE_CLOUD_PROJECT=x ../.venv/bin/python test_app.py
"""
import asyncio

import app


async def main():
    r = await app.run_malloy("run: operations -> { where: close_day = @2026-06-15; aggregate: fees_xlm }")
    assert round(r["rows"][0]["fees_xlm"], 2) == 6670.62, r  # README / daily_fee_stats_agg value

    r = await app.run_malloy("run: operations -> { where: close_day = @2026-06-15; aggregate: naive is fee_charged.sum() / 10000000 }")
    assert round(r["rows"][0]["naive"], 2) == 13383.02, r  # the double count still exists in the data

    for bad in ["select 1",
                "run: duckdb.table('/etc/passwd') -> { select: * }",
                'run: operations -> { select: * } import "x.malloy"']:
        assert "error" in await app.run_malloy(bad), bad
    assert "error" in await app.run_malloy("run: operations -> { aggregate: x is nonsense.sum() }")
    assert "permission" in str(_try("select * from read_csv('/etc/hosts')")).lower()
    print("ok")


def _try(sql):
    try:
        app._execute(sql)
    except Exception as e:
        return e


asyncio.run(main())

"""One-time export: a year of enriched_history_operations, rolled up, to Parquet.

    .venv/bin/python extract_rollup.py --project <your-billing-project>

Grain: (close_day, type_string, txn_operation_count). Every row in a group shares
one txn_operation_count, so fee_charged / txn_operation_count stays exact and a
naive SUM(fee_charged) still double-counts, exactly as on the raw table.
Scans ~170 GB once; the output is a few MB.
"""
import argparse

import pyarrow.parquet as pq
from google.cloud import bigquery

SQL = """
select
  date(closed_at) as close_day,
  type_string,
  txn_operation_count,
  count(*) as op_rows,
  sum(fee_charged) as fee_charged
from `crypto-stellar.crypto_stellar_dbt.enriched_history_operations`
where closed_at >= @start and closed_at < @end
group by 1, 2, 3
order by 1, 2, 3
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--project", required=True, help="billing project")
    p.add_argument("--start", default="2025-10-01")
    p.add_argument("--end", default="2026-10-01")
    p.add_argument("--out", default="data/operations_daily.parquet")
    a = p.parse_args()

    client = bigquery.Client(project=a.project)
    job = client.query(SQL, job_config=bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("start", "TIMESTAMP", a.start),
            bigquery.ScalarQueryParameter("end", "TIMESTAMP", a.end),
        ],
        maximum_bytes_billed=250 * 10**9,
    ))
    table = job.to_arrow()
    pq.write_table(table, a.out, compression="zstd")
    print(f"{table.num_rows} rows -> {a.out} ({job.total_bytes_billed / 1e9:.1f} GB billed)")


if __name__ == "__main__":
    main()

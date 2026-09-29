# Data questions in this repo

`fees.malloy` is the definition of record for network fee metrics. Read it before
answering any question about fees, transactions, or operations.

## How to answer
1. Find the measure or view in `fees.malloy` that answers the question and use it
   by name. Do not write inline aggregates like `sum(fee_charged)` in a query.
2. Run queries through `ask.py`, which exposes one tool: `run_malloy`. There is no
   SQL tool. If a question needs a measure that does not exist, say so and
   propose it as a change to `fees.malloy` rather than inventing it in a query.
3. Every query filters `closed_at` to a day or a short range. The table is large.
4. Report the measure used and quote its `#` comment.

## What you must not do
- Do not query BigQuery directly for a metric that `fees.malloy` defines.
- Do not filter fees to successful transactions. Failed transactions pay too.
- Do not answer from memory. If the query did not run, say so.

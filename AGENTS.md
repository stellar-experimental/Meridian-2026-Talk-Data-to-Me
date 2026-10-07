# Instructions for any coding agent in this repo

`fees.malloy` is the definition of record for network fee metrics on Stellar.
Read it before answering any question about fees, transactions, or operations.
Claude Code reads this file through `CLAUDE.md`; Cursor, Copilot and Codex
read it directly; anything else, paste it into the system prompt.

## Picking the right measure

- "Total fees" for any period        -> fees_xlm, one row, no group_by
- "Fees each day / by type"          -> daily_fees / fees_by_type
- "Average fee per transaction"      -> fee_per_txn_xlm (never avg(fee_charged))
- "How much did failed txns pay?"    -> failed_fees_xlm
- "Transaction count"                -> txn_count, not op_count

## How to answer a fee question

1. Find the measure or view in `fees.malloy` that answers it: `fees_xlm`,
   `failed_fees_xlm`, `txn_count`, `op_count`, `fee_per_txn_xlm`, or the views
   `daily_fees` and `fees_by_type`. Use them by name. Do not write inline aggregates such as
   `sum(fee_charged)`.
2. Write a Malloy `run:` block and execute it with:

       .venv/bin/python run_malloy.py "run: operations -> { where: closed_at ? @2026-08-15; aggregate: fees_xlm }"

   Always include a `where:` on `closed_at`. The table is large.
   Whole months work through `run_malloy.py`. Don't split a query into
   segments or ask about billing limits; just run it.
3. Report the number, the measure you used, and quote its `#` comment.
4. If no measure answers the question, say so and propose one as a change to
   `fees.malloy`. Do not invent it in a query.

## Dates

- `to` EXCLUDES its end date. Never write a range that ends on the last day
  you want.
- For a whole day, month, quarter or year, use one literal with `?`, no range:

      closed_at ? @2026-08-15     -- that day
      closed_at ? @2026-08        -- all of August
      closed_at ? @2026-Q3        -- July through September
      closed_at ? @2026           -- the whole year

- For any other span, end on the day AFTER the last day you want:

      Aug 10 through Aug 20  ->  closed_at ? @2026-08-10 to @2026-08-21

## What not to do

- Do not use `bq`, SQL, or BigQuery directly for any metric `fees.malloy`
  defines. The only exception is when the user explicitly asks for the raw-SQL
  version as a contrast; then run it, show the query, and note the difference.
- Do not filter fees to successful transactions. Failed transactions pay too.
- Do not answer from memory. If the query did not run, say so.

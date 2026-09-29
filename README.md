# Talk Data to Me

A semantic layer on one public Stellar table, and two small agents that show
why it matters. Companion repo for the Meridian 2026 talk *Talk Data to Me:
Onboarding an LLM to your Warehouse*.

The table is `crypto-stellar.crypto_stellar_dbt.enriched_history_operations`.
One row per operation. Fees are charged per **transaction**, and the
transaction's fee is copied onto every one of its operation rows. Nothing in
the schema says so. A model that sums `fee_charged` gets a number that is
exactly twice too high, formatted nicely, with no error.

| June 15, 2026 | XLM |
|---|---|
| `SUM(fee_charged)` on operation rows | 13,383.02 |
| Through the semantic layer (`fees_xlm`) | 6,670.62 |
| `daily_fee_stats_agg`, the dbt mart | 6,670.62 |

## What is here

| File | What it is |
|---|---|
| `fees.malloy` | The semantic layer. One source, four measures, two views, two named queries. The comments are the guidance an LLM reads. |
| `ask.py` | Claude with **one tool: run a Malloy query**. No SQL tool exists. |
| `ask_raw.py` | Claude with **one tool: run SQL**, and a schema of names and types. The contrast case. |
| `fees_local.malloy` | The same idea on a ten-row CSV with DuckDB. Runs with no cloud account. |
| `data/` | The ten-row dummy tables from the talk. |
| `CLAUDE.md` | The guidance layer, as a file Claude Code reads automatically. |

## Run it offline, five minutes

1. Install [VS Code](https://code.visualstudio.com) and the **Malloy** extension.
2. Clone this repo and open the folder.
3. Open `fees_local.malloy`. Click the grey **Run** link above the first block.

Block 2 returns 3,200. Block 5 returns 1,100. The difference is one `join_one`
declaration. No account, no cloud, no cost.

## Run it on the real table

```bash
gcloud auth application-default login
gcloud config set project <your-billing-project>

python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...

python ask.py     "What were network fees on June 15, 2026?"
python ask_raw.py "What were network fees on June 15, 2026?"
```

`ask.py` prints the Malloy query the model chose and the answer.
`ask_raw.py` prints the SQL the model wrote and the answer. Same model, same
question, same table. The only difference is which tool it was handed.

Each run scans about one day of operations. Keep the `where:` on `closed_at`.
`ask_raw.py` caps each query at 2 TB billed (`BQ_MAX_BYTES` to change).

To use the model file in VS Code instead, add a BigQuery connection named
`bigquery` in the Malloy panel with your billing project, open `fees.malloy`,
and click Run above `fees_june_15`.

## What this repo does not do

- **No gated access.** `ask.py` denies SQL by construction, but nothing stops
  someone from running `ask_raw.py`. In production the gate is the tool list
  the agent is given, enforced outside the model.
- **No evals.** A prompt set and a judge that grade the agent's answers
  against known numbers. That is the step that catches drift.
- **No USD.** There is no public XLM price table, so fees stay in XLM.
- **No scale.** One table, four measures. A real warehouse has hundreds of
  tables and the same problem on every one.

## Credits

Export-to-DuckDB pattern from
[stellar-shoestring-analytics](https://github.com/sydneynotthecity/stellar-shoestring-analytics).
Public Stellar data from [Hubble](https://developers.stellar.org/docs/data/analytics/hubble)
and [stellar-dbt-public](https://github.com/stellar/stellar-dbt-public).

Apache 2.0.

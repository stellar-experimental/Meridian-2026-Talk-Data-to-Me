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
| `run_malloy.py` | Runs one Malloy query on BigQuery and prints rows plus the generated SQL. What Claude Code calls. |
| `ask.py` | Claude with **one tool: run a Malloy query**. No SQL tool exists. Needs an API key. |
| `ask_raw.py` | Claude with **one tool: run SQL**, and a schema of names and types. The contrast case. Needs an API key. |
| `CLAUDE.md` | The guidance layer, as a file Claude Code reads automatically. |

## Ask Claude Code, no API key

```bash
gcloud auth application-default login
gcloud config set project <your-billing-project>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
claude
```

Then ask: *What were network fees on August 15, 2026?*
Claude reads `CLAUDE.md`, picks `fees_xlm` from `fees.malloy`, runs it through
`run_malloy.py`, and answers. It writes no SQL.

Then ask: *Now answer with raw SQL against the BigQuery table, ignoring the Malloy file.*
It writes `SUM(fee_charged)` and returns about twice the number.

## Scripted version, needs an Anthropic API key

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
and click Run above `fees_august_15`. The extension caps each query at 25 GB
billed by default; raise Maximum Bytes Billed on the connection for windows
wider than a week.

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

Public Stellar data from [Hubble](https://developers.stellar.org/docs/data/analytics/hubble)
and [stellar-dbt-public](https://github.com/stellar/stellar-dbt-public).

Apache 2.0.

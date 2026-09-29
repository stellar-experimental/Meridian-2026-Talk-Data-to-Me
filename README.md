# Talk Data to Me

A semantic layer on one public Stellar table, and the setup for any coding
agent to query through it instead of writing SQL. Companion repo for the Meridian 2026 talk *Talk Data to Me:
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
| `run_malloy.py` | Runs one Malloy query on BigQuery and prints rows plus the generated SQL. What the agent calls. |
| `AGENTS.md` | The guidance layer. Read by Cursor, Copilot and Codex directly, and by Claude Code through `CLAUDE.md`. |

## Ask your agent, no API key

```bash
git clone https://github.com/stellar-experimental/Meridian-2026-Talk-Data-to-Me.git
cd Meridian-2026-Talk-Data-to-Me
gcloud auth application-default login
gcloud config set project <your-billing-project>
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
claude
```

The billing project is any Google Cloud project you belong to. If you have
none, create one in the console; no billing account is needed for these
amounts. The data itself is public and read from `crypto-stellar`; your
project only pays for the bytes your queries scan.

The last line starts Claude Code. Cursor, Copilot, Codex or Gemini CLI work the
same way: open the folder and ask. They all read `AGENTS.md`. Any other agent,
including a chat window that runs nothing, can be shown `fees.malloy` and asked
which measure it would pick.

## The two prompts

Asked in the agent, started in this folder.

> What were network fees on August 15, 2026?

The agent reads `fees.malloy`, picks `fees_xlm`, runs it through `run_malloy.py`,
and answers about 4,565 XLM with the measure's comment quoted. No SQL.

> Now answer the same question with raw SQL against the BigQuery table, ignoring the Malloy file.

It writes `SUM(fee_charged)` and answers about twice that. Same model, same
table, same question. The only difference is what it was told to use.

## What this repo does not do

- **No hard gate.** The agent avoids SQL here because `AGENTS.md` asks it
  to; it still has a shell. In production the gate is the tool list the agent
  is given, enforced outside the model, so a SQL tool does not exist at all.
- **No evals.** A prompt set and a judge that grade the agent's answers
  against known numbers. That is the step that catches drift.
- **No USD.** There is no public XLM price table, so fees stay in XLM.
- **No scale.** One table, four measures. A real warehouse has hundreds of
  tables and the same problem on every one.

## Credits

Public Stellar data from [Hubble](https://developers.stellar.org/docs/data/analytics/hubble)
and [stellar-dbt-public](https://github.com/stellar/stellar-dbt-public).

Apache 2.0.

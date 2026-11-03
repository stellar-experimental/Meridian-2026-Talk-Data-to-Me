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
| `fees.malloy` | The semantic layer. One source, five measures, two views, three named queries. The comments are the guidance an LLM reads. |
| `run_malloy.py` | Runs one Malloy query on BigQuery and prints rows plus the generated SQL. What the agent calls. |
| `AGENTS.md` | The guidance layer. Read by Cursor, Copilot and Codex directly, and by Claude Code through `CLAUDE.md`. |
| `web/` | The web demo from the talk: a phone-sized page where Claude answers fee questions with one tool, `run_malloy`, over a DuckDB copy of the data. |
| `data/operations_daily.parquet` | A year of the table (2025-10-01 to 2026-09-30) rolled up by day, operation type and ops per transaction. What the web demo queries. |
| `extract_rollup.py` | Rebuilds that Parquet file from BigQuery. |
| `Dockerfile` | Packages the web demo for Cloud Run or any container host. |

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

## Run the web demo yourself

The web demo needs no BigQuery access: it reads the bundled Parquet rollup
through DuckDB. It does need Claude, through either an Anthropic API key or
Claude on Vertex AI.

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -r web/requirements.txt
python -c "import duckdb; duckdb.connect('web/operations.duckdb').execute(\"create table operations_daily as from 'data/operations_daily.parquet'\")"

cd web
GOOGLE_CLOUD_PROJECT=x python test_app.py   # self-check of the tool gate and measures, no model calls, prints "ok"

export ANTHROPIC_API_KEY=sk-ant-...         # or, for Vertex: export GOOGLE_CLOUD_PROJECT=<project>
uvicorn app:app --port 8080
```

Open http://localhost:8080. The `web/requirements.txt` pins are tested on
Python 3.12, the version the Dockerfile uses.

For Vertex, run `gcloud auth application-default login`, then enable Claude
Haiku 4.5 in Model Garden for the project. With neither variable set, the app
will not start.

| Variable | Default | What it does |
|---|---|---|
| `ANTHROPIC_API_KEY` | unset | Use the Anthropic API. When set, takes precedence over Vertex. |
| `GOOGLE_CLOUD_PROJECT` | unset | Use Claude on Vertex AI in this project (region `global`). |
| `CLAUDE_MODEL` | `claude-haiku-4-5` (Vertex: `claude-haiku-4-5@20251001`) | Model ID. |
| `RATE_LIMIT_QUESTIONS` / `RATE_LIMIT_WINDOW_S` | `100` / `300` | Questions per client IP per window. Sized for a conference room behind one NAT address. |

### In a container

```bash
docker build -t talk-data-to-me .
docker run --rm -p 8080:8080 -e ANTHROPIC_API_KEY talk-data-to-me
```

The image builds `operations.duckdb` itself, so you can skip the step above.

### On Cloud Run

```bash
gcloud run deploy talk-data-to-me --source . --region us-central1 \
  --allow-unauthenticated --set-env-vars GOOGLE_CLOUD_PROJECT=<project>
```

The service account needs `roles/aiplatform.user` in that project. To use an
API key instead, store it in Secret Manager and pass
`--set-secrets ANTHROPIC_API_KEY=<secret>:latest`. The page is public and
every question costs model tokens, so lower the rate limit or drop
`--allow-unauthenticated` if the URL will travel.

### Refreshing the data

`extract_rollup.py` rebuilds the Parquet file for any date range from the
public table `crypto-stellar.crypto_stellar_dbt.enriched_history_operations`.
It scans about 170 GB for a year, billed to your own billing project:

```bash
pip install -r requirements.txt pyarrow     # in the agent-path venv, after gcloud auth
python extract_rollup.py --project <billing-project> --start 2025-10-01 --end 2026-10-01
```

If you change the range, update the coverage dates in the system prompt in
`web/app.py` and the subtitle in `web/index.html`. The prompt tells Claude
what the data covers.

## What this repo does not do

- **No hard gate on the agent path.** The agent avoids SQL here because
  `AGENTS.md` asks it to; it still has a shell. In production the gate is the
  tool list the agent is given, enforced outside the model, so a SQL tool does
  not exist at all. The web demo is built that way: Claude gets only
  `run_malloy`.
- **No evals.** A prompt set and a judge that grade the agent's answers
  against known numbers. That is the step that catches drift.
- **No USD.** There is no public XLM price table, so fees stay in XLM.
- **No scale.** One table, five measures. A real warehouse has hundreds of
  tables and the same problem on every one.

## Credits

Public Stellar data from [Hubble](https://developers.stellar.org/docs/data/analytics/hubble)
and [stellar-dbt-public](https://github.com/stellar/stellar-dbt-public).

Apache 2.0.

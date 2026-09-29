# Stage script, about two minutes

Setup before walking on: VS Code in Zen Mode, zoomed so ~20 lines fill the
screen, results panel docked right. A terminal with the venv active and
ANTHROPIC_API_KEY exported. Screenshots of every result as backup slides.

1. **Open `fees.malloy`.** Scroll nowhere. Point at the measure `fees_xlm`
   and its comment. "Twelve lines. This is the semantic layer. The comment is
   the part the model reads."

2. **Terminal: `python ask_raw.py`.** Watch it print `[run_sql]` and a query
   with `SUM(fee_charged)`. Answer: about 13,383 XLM.
   "Raw warehouse. Names and types. The model did the obvious thing."

3. **Terminal: `python ask.py`.** Watch it print `[run_malloy]` and a query
   that names `fees_xlm`. Answer: 6,670.62 XLM.
   "Same model, same question, same table. It picked a measure instead of
   writing a sum. The layer wrote the SQL and divided."

4. **Say the line.** "The only difference is which tool it was handed. This
   repo is public. The table is public. You can run this tonight."

Fallback if wifi fails: the screenshots of both terminal runs.

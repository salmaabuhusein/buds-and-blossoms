# Buds & Blossoms

Plant search engine for the USI Information Retrieval 2026-27 course project (topic 13, pair project).
Code and report (max. 10 pages including cover) are due on iCorsi by 15 December 2026. A user evaluation with three classmates is required; system evaluation (precision/recall) is not.

Required: at least one complex and one simple feature. Ours are relevance feedback (complex) and results table, filtering and highlighted snippets (simple).

## Commands
Run from the repo root. Python is 3.9, so use `List`/`Optional`, not `list[str]`/`X | None`.

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn backend.app:app --reload --port 8000   # API
cd frontend && npm install && npm run dev                # UI on :5173, proxies /api to :8000
cd frontend && npm run build                             # check that the frontend compiles
.venv/bin/python crawler/crawl.py                        # rebuild data/plants.jsonl
```

`.venv/bin/python eval/relevance.py [--compare] [--per-query]` checks ranking on test queries judged from the records (P@10, MAP, known-item MRR, simulated feedback). Run it after any ranking change. Porter and Krovetz in `--compare` need `nltk` / `krovetzstemmer`, which are not in requirements.

There are no automated tests or linters. The index is built in memory at startup, so restart the API after changing `data/plants.jsonl` (`--reload` only watches Python files).

## Architecture
`crawler/crawl.py` → `crawler/normalize.py` → `data/plants.jsonl` → `indexer/index.py` → `backend/app.py` → `frontend/src/App.jsx`

- **crawl.py**: for each source (`mbg`, `ncsu`, `wf`), a URL generator and a parser. A parser returns raw fields (`color_raw`, `sun_raw`, ...) or `None`.
- **normalize.py**: the only place that maps site vocabulary to the shared schema.
- **inverted.py**: inverted index, BM25 with IDF `log((M+1)/df)` over weighted queries, a bigram index for phrase bonuses, and Rocchio (α 8, β 16, γ 4; new terms must occur in 2+ marked plants). Knows nothing about plants.
- **index.py**: tokenising, stop list, plural stemming (swappable via `STEMMER`), query terms and phrases, field weights, search, facet counts, snippets and highlighting.
- **app.py**: thin layer with `GET /api/search` (paged: `page`, `page_size` default 50, max 200; total and facets cover all hits) and `GET /api/stats`. The UI asks for 48 per page and returns to page 1 on any new query, filter, sort or feedback.
- **App.jsx / styles.css**: the whole UI. No router, state library or CSS framework.

Filters combine with OR inside an attribute and AND across attributes. Facet counts ignore their own attribute's filter.

## Rules and gotchas
- **Crawler etiquette**: keep the robots.txt check, the 1 s delay and the page cache. Garden.org and Gardenia.net return 403; do not work around that.
- **Keep `data/raw/`** (about 250 MB, gitignored): it makes rebuilds offline. Deleting it means re-crawling for about 2 hours.
- **`crawl.py` overwrites all of `plants.jsonl`**, even with `--only` or when a source fails. Back it up and diff afterwards.
- **Record `id`s** are hashes of the URL, set when the index loads; the `id` in `plants.jsonl` is only a row number.
- **NC State pages** use several `<dd>` per `<dt>`; read all of them. Photos must exclude `partner_logos`. Alias pages (`/common-name/<alias>/`, 2,573 of the 6,718 candidate pages) put the alias in front of the scientific name in the `<h1>`: take the scientific name from its `<em>`.
- **Wildflower Center** is parsed line by line because multi-line regexes backtracked catastrophically. "Light" fields can include unrelated page text.
- **Query and document text must go through the same `tokenize()`**. Query-only steps (dropping generic words, fall/autumn expansion) belong in `query_concepts()`.
- **Highlighting** works on escaped HTML that React inserts with `dangerouslySetInnerHTML`: always `html.escape()` first, and never mark inside entities.
- **Normaliser changes** can shift which plants qualify (500 per source, needing a colour and a photo). Compare the dataset before and after.
- **Sampling**: each source's candidate pages are shuffled with a fixed seed (`spread()`), so the first 500 usable plants are spread over the whole site and a rebuild from the cache gives the same records. Don't reintroduce alphabetical walks.

## Current state
Relevance feedback works in the table and grid: "Update results" sends `relevant` / `rejected` ids; ✓ expands the query (Rocchio), ✗ removes the plant and, together with a ✓, lowers the weight of terms it shares with the ✓ plants. A new search resets it. `?feedback=off` in the UI address hides it for the evaluation baseline. Nothing is logged yet.

Known limits:
- Any one query word matches, so results are broad. Scores favour records matching more query words; phrases count only in names (in descriptions they hurt P@10). With a query, feedback only re-ranks the plants matching it (plus the ✓ ones) and adds none. When browsing, feedback keeps plants that have at least half of the expansion values ("Also looking for"); multi-word attribute values such as "partial shade" count as one value.
- 537 records have no zone (all 500 Wildflower Center ones: the site has none), 318 have no light data (314 Wildflower Center pages have no growing conditions) and 284 have generated descriptions (283 Wildflower Center).
- 25 scientific names appear in more than one source.

## Planned
1. Logging for the evaluation (time, queries, marks).
2. Merge cross-source duplicates; label generated descriptions.
3. Notices for records hidden by missing data.
4. Pilot, then the evaluation: time, number of queries, plants found and SUS.

## Working conventions
- Commit or push only when asked.
- Verify UI changes in a browser at desktop and phone width.
- Check every number quoted in a report against the running code.
- Do not change report wording beyond what was asked.
- Keep the look: Playfair Display and DM Sans, cream/plum/sage palette, plain-text seasons and zones.
- Never commit `project-instructions*.pdf`; it contains students' names.

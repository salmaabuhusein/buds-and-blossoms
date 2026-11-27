# Buds & Blossoms — botanical search

IR course project (USI 2026-27, topic 13: Plants and flowers).

## Layout
| Folder | What |
|---|---|
| `crawler/` | `crawl.py` scrapes 3 sources → `data/plants.jsonl`; `normalize.py` maps each site's vocabulary to one schema |
| `indexer/` | `inverted.py`: inverted index, BM25 with field weights, word-pair (phrase) bonus, Rocchio; `index.py`: stop list, plural stemming, search, facets, highlighted snippets, paging |
| `backend/` | FastAPI: `GET /api/search` (paged), `GET /api/stats` |
| `data/` | `plants.jsonl`, the 1,500 crawled records, 500 per source (cached pages in `data/raw/` are not in git) |
| `eval/` | `relevance.py`: offline check of ranking changes (P@10, MAP, search by plant name, simulated feedback) on test queries judged from the records |
| `report/` | Progress report |
| `frontend/` | React + Vite UI: search, filters, table and grid views, pages of 48, relevance feedback |

Sources: Missouri Botanical Garden Plant Finder, NC State Extension Plant Toolbox, Lady Bird Johnson Wildflower Center.
(Garden.org and Gardenia.net return 403 to automated clients, so they are not crawled.)

## Run
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/uvicorn backend.app:app --port 8000            # terminal 1
cd frontend && npm install && npm run dev                # terminal 2 -> http://localhost:5173
```

Optional: rebuild `data/plants.jsonl` (it is in git) and check the ranking after changes:

```bash
.venv/bin/python crawler/crawl.py --per-source 500      # ~2 hours first time, cached afterwards
.venv/bin/python eval/relevance.py                      # P@10, MAP, ...; --compare for the settings comparison
```

## Features
- Results in a table, 48 per page (simple)
- Filtering on flower colour, bloom season, sun, USDA zone, plant type, source (simple)
- Highlighted result snippets (simple)
- User relevance feedback with Rocchio (complex): mark plants ✓/✗, then "Update results". ✓ expands and re-weights the query, ✗ removes the plant. `?feedback=off` in the UI address hides it (evaluation baseline)

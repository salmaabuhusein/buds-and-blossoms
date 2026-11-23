# Buds & Blossoms — botanical search

IR course project (USI 2026-27, topic 13: Plants and flowers).

## Layout
| Folder | What |
|---|---|
| `crawler/` | `crawl.py` scrapes 3 sources → `data/plants.jsonl`; `normalize.py` maps each site's vocabulary to one schema |
| `indexer/` | `index.py` — BM25 index (field-boosted), facet counts, Google-style highlighted snippets |
| `backend/` | FastAPI: `GET /api/search`, `GET /api/stats` |
| `data/` | `plants.jsonl`, the 600 crawled records (cached pages in `data/raw/` are not in git) |
| `report/` | Progress report |
| `frontend/` | React + Vite UI: search, filters, table and grid views |

Sources: Missouri Botanical Garden Plant Finder, NC State Extension Plant Toolbox, Lady Bird Johnson Wildflower Center.
(Garden.org and Gardenia.net return 403 to automated clients, so they are not crawled.)

## Run
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python crawler/crawl.py --per-source 200      # ~30-60 min first time, cached afterwards
.venv/bin/uvicorn backend.app:app --port 8000            # terminal 1
cd frontend && npm install && npm run dev                # terminal 2 -> http://localhost:5173
```

## Features
- Results in a table (simple) 
- Filtering on flower colour, bloom season, sun, USDA zone, plant type, source (simple)
- Highlighted result snippets (simple)
- User relevance feedback with Rocchio re-ranking (complex) — currently ✓/✗ buttons only; they do not change the ranking yet

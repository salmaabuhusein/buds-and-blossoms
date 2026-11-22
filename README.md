# Buds & Blossoms — botanical search

IR course project (USI 2026-27, topic 13: Plants and flowers).

## Layout
| Folder | What |
|---|---|
| `crawler/` | `crawl.py` scrapes 3 sources → `data/plants.jsonl`; `normalize.py` maps each site's vocabulary to one schema |
| `indexer/` | `index.py` — BM25 index (field-boosted), facet counts, Google-style highlighted snippets |
| `backend/` | FastAPI: `GET /api/search`, `GET /api/stats` |
| `frontend/` | React + Vite UI built from `mockup.png` |

Sources: Missouri Botanical Garden Plant Finder, NC State Extension Plant Toolbox, Lady Bird Johnson Wildflower Center.
(Garden.org and Gardenia.net return 403 to automated clients, so they are not crawled.)

## Run
```bash
python3 -m venv .venv && .venv/bin/pip install requests beautifulsoup4 lxml fastapi uvicorn rank_bm25 scikit-learn
.venv/bin/python crawler/crawl.py --per-source 200      # ~30-60 min first time, cached afterwards
.venv/bin/uvicorn backend.app:app --port 8000            # terminal 1
cd frontend && npm install && npm run dev                # terminal 2 -> http://localhost:5173
```

## Features
- Results in a table (simple) ✅
- Filtering on flower colour, bloom season, sun, USDA zone, plant type, source (simple) ✅
- Highlighted result snippets (simple) ✅
- User relevance feedback with Rocchio re-ranking (complex) — UI buttons in place, backend next

"""FastAPI search service.  Run:  .venv/bin/uvicorn backend.app:app --reload --port 8000"""
import sys
from collections import Counter
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from indexer.index import PlantIndex  # noqa: E402

app = FastAPI(title="Buds & Blossoms")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
index = PlantIndex()


@app.get("/api/stats")
def stats():
    by_source = Counter(d["source"] for d in index.docs)
    return {"records": len(index.docs), "sources": len(by_source), "by_source": by_source}


@app.get("/api/search")
def search(
    q: str = "",
    colors: List[str] = Query([]),
    seasons: List[str] = Query([]),
    sun: List[str] = Query([]),
    type: List[str] = Query([]),
    source: List[str] = Query([]),
    zone: Optional[int] = None,
    sort: str = "relevance",
    relevant: List[str] = Query([]),
    rejected: List[str] = Query([]),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    filters = {"colors": colors, "seasons": seasons, "sun": sun, "type": type, "source": source, "zone": zone}
    return index.search(q, filters, sort, relevant, rejected, page, page_size)

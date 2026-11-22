# Buds & Blossoms: Progress Report
**Information Retrieval 2026-27, Project 13: Plants and Flowers**
Jana Srbakoska, Salma Abu Husein · 24 November 2026

## Sources and document counts
| Source | How pages are found | Records |
|---|---|---|
| Missouri Botanical Garden Plant Finder | A–Z list pages | 200 |
| NC State Extension Plant Toolbox | sitemap.xml | 200 |
| Lady Bird Johnson Wildflower Center | search by plant family | 200 |

We checked robots.txt and access for each candidate site. The suggested site, Garden.org, and our planned fourth source, Gardenia.net, reject automated requests (HTTP 403), so we used the three sites above, which cover the same kind of content. The crawler waits 1 s between requests and caches every page. We keep only flowering plants that have a photo, which gives **600 records**.

## Schema
Each site describes plants differently ("Part shade" vs. "Dappled sunlight", "April to May" vs. "Jun, Jul, Aug"). A normaliser maps every record onto one schema:

`name · scientific_name · family · type · description · photo · colours[] · seasons[] · sun[] · zone_min/max · source · url`

## Chosen features
| Feature | Type | Status |
|---|---|---|
| Results presented in a table | simple | working |
| Filtering on ≥3 attributes (colour, season, sun, zone, type, source) | simple | first version working; to be refined 25 Nov–2 Dec |
| User relevance feedback (Rocchio, positive feedback) | complex | ✓/✗ buttons in the UI; re-ranking planned for 25 Nov–2 Dec |
| Highlighted result snippets | simple (stretch goal) | early version working; polish 3–5 Dec |

We chose relevance feedback because gardening queries are often vague ("shade plant", "something pink"). Letting users mark plants they like is a natural way to narrow the results.

## Architecture
```
crawler (requests + BeautifulSoup) ─► normaliser ─► data/plants.jsonl
                                                          │
                                         indexer (BM25, field boosting)
                                                          │
                              FastAPI backend: /api/search, /api/stats
                                                          │
                                       React UI (search, filters, table)
```

## What works
- Crawling, cleaning and de-duplication across all three sources.
- BM25 search over the name, scientific name, attributes and description, with stop-word removal and light stemming.
- A minimal UI: search bar, results table with a photo per plant, sorting, and the first version of the filters.

> **[Insert screenshot of the results page here]**

## Division of work so far
- **Jana:** spiders for sources 1–2, indexer and ranking, backend API, UI mockup.
- **Salma:** spider for source 3, normaliser, data cleaning and statistics, this progress page.

## Next steps
- **25 Nov–2 Dec:** replace the current light stemmer with the Krovetz stemmer (it keeps real words, so plant names and highlighted snippets stay readable) and build our own inverted index (dictionary + postings) in place of the BM25 library; on top of it, implement Rocchio relevance feedback with positive feedback only (α = 8, β = 16), keeping the top terms of the relevant centroid, while ✗-marked plants are removed from the re-ranked list (Jana). Finish the filters and facet UI (Salma).
- **3–5 Dec:** polish the snippets, run a pilot test, book 3 test users, prepare the evaluation materials.
- **6–10 Dec:** user evaluation with three classmates, comparing the system with feedback off (baseline) and on (experimental) on given search tasks in a Latin-square order, measuring time, queries and relevant plants found, plus SUS and short post-task questionnaires.
- **10–15 Dec:** analysis, report and code submission.

Known limitation: the Wildflower Center does not list hardiness zones, so its records are excluded when the user filters by zone.

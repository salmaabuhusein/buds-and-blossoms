# Buds & Blossoms: Progress Report
Information Retrieval, Project 13: Plants and Flowers. 
Jana Srbakoska, Salma Abu Husein

## Goal and collection
Buds & Blossoms supports specific and vague plant searches, e.g. "something pink for winter". We crawled 600 records, 200 from each of the following: the Missouri Botanical Garden Plant Finder (A–Z lists), NC State Extension Plant Toolbox (sitemap) and Lady Bird Johnson Wildflower Center (family search). Garden.org and Gardenia.net both rejected automated requests (HTTP 403). 
The crawler checks robots.txt, waits 1 second between requests and caches pages. Site specific parsers normalise attributes/vocabularies onto a shared schema e.g. "dappled sunlight" becomes partial shade.


## Current implementation
| IR process | Implementation |
|---|---|
| Acquisition/ Indexing | Site-specific crawling and normalisation; lower-casing, stop-word removal and basic plural stemming. A bag-of-words representation boosts names and attributes by repetition |
| Query processing/ Retrieval | Matching preprocessing; removal of generic terms (“flower”, “plant”) when other terms remain; fall/autumn expansion. BM25 ranking (`rank_bm25`, k1 = 1.5, b = 0.75) with Boolean filters. |
| UI (simple features) | React table/grid, six attribute filters, sorting and query-highlighted snippets. FastAPI serves results from an in-memory BM25 representation. |
| Relevance feedback (complex feature) | ✓/✗ buttons in the table; they do not change the ranking yet |

Architecture: Data acquisition and indexing: requests, BeautifulSoup, JSON Lines, in-memory BM25 index. Backend and interface: FastAPI, React.

![Results page](screenshot.png)

## Findings and Limitations
For “pink orchid”, 166 records match at least one term; only 16 contain both. Roundleaf Orchid scores 9.64 (“orchid”: 7.41; “pink”: 2.23). rank_bm25 floors negative IDFs, so frequent “flower” (557 records) receives IDF 1.28, higher than “pink” (159 records; 1.02). 
Excluding generic terms reduces “winter flowers” matches from 572 to 237. “Climbing” and “climber” do not match, and misspellings return no results. Sampling is uneven; 216 records lack zones, 96 lack light data, and 88 descriptions are generated from structured fields.


## How we will improve and expand
- We will implement Rocchio-style positive-feedback query expansion using BM25-weighted vectors and exclude negatively marked results. 
- We will build an inverted index with explicit field weights and revised IDF (log((M+1)/df)); prioritise matches covering more query terms and compare stronger stemmers. 
- We will expand and balance the collection, deduplicate cross-source plants, label generated descriptions, and add pagination, visible expansion terms/reset and missing-data notices. 
- After a pilot, three of our classmates will test feedback off vs. on; we will record time, number of queries, plants found and SUS responses. 


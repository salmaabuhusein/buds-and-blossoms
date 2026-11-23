# Buds & Blossoms as an Information Retrieval System

Information Retrieval 2026-27 · Project 13: Plants and Flowers · Status: 23 November 2026

This report explains the project through the concepts of the course. References such as [03:38] mean lecture file 03, PDF page 38. **Built** parts are distinguished from **planned** ones throughout. Measurements use the current collection of 600 records.

## 1. The retrieval problem

A gardener has an *information need*, such as "something pink for a shady corner", and expresses it as a query. The query is only a hint: the set of relevant documents R(q) is unknown and user-dependent, so the system computes an approximation R′(q) [02:29]. Queries may also be under-specified or ambiguous [02:23]. "Rose", for example, can be a plant or a colour.

Our data are *semi-structured*: each record has typed attributes and free text. The system therefore combines two kinds of retrieval [01:16, 02:30].

| | Filters | Text search |
|---|---|---|
| Course strategy | Document selection | Document ranking |
| Match | Exact: true or false | Partial: a score |
| Model | Boolean | BM25 |
| Example | Colour = Pink AND Season = Spring | "pink orchid" |

Within a filter attribute, values are combined with OR; attributes are combined with AND. Text ranking avoids having to decide absolute relevance, following the argument that relevance is a matter of degree [02:32]. The Probability Ranking Principle justifies ordering by probability of relevance, assuming that users read sequentially and that results have independent utility [02:33]. The second assumption is imperfect here, because 11 scientific names occur in more than one source.

The system works in *pull* mode and supports both *querying* and *browsing* [02:4, 02:6]: an empty search lists all plants, and filters structure the exploration.

## 2. The IR process in the project

| Course sub-process [02:12] | Our component | Status |
|---|---|---|
| Indexing: acquisition | `crawler/crawl.py` | Built |
| Indexing: transformation | `normalize.py`, `tokenize()` | Built |
| Indexing: index creation | `PlantIndex` with `rank_bm25` | Built; no inverted index |
| Query process | `query_terms()` | Built |
| Retrieval process | `score()` and `search()` | Built |
| Relevance feedback | ✓/✗ buttons | Buttons only |

Acquisition and normalisation happen *offline*; queries are handled *online* [05:5]. The index is built in memory whenever the backend starts.

## 3. Acquisition and transformation

Three sites supply 200 records each. The crawler checks robots.txt, waits one second between requests and caches pages. Site-specific parsers use the page structure and labelled fields to extract content, which addresses the problem of separating content from noise [05:8, 05:10].

The normaliser maps different vocabularies to one: "Dappled sunlight" becomes Partial shade. This reduces vocabulary mismatch, the difficulty that the same thing can be said in many ways [01:14].

**Collection bias.** By scientific name, NC State covers A–C and Missouri A–K, and 95 of 200 Wildflower Center records start with A. No ranking method can retrieve plants that are not in the collection. In addition, 88 descriptions are generated from structured fields, so their text is not source prose.

## 4. Text processing

### Tokenisation and stopping
Text is lower-cased and split into alphanumeric sequences, close to the course's basic tokeniser [05:20]. Stop words are removed both when indexing and when querying. The lecture recommends indexing everything and deciding at query time [05:28]; our fixed list departs from this.

### Zipf's law in our collection
The descriptions and additional text contain 138,576 tokens and 7,835 distinct words before stopping; 3,176 words occur only once. Zipf's law predicts that rank × probability is roughly constant, about 0.1 for English [05:14].

| Rank | Word | Count | r · Pr |
|---|---|---|---|
| 1 | the | 5,536 | 0.040 |
| 2 | in | 4,735 | 0.068 |
| 3 | and | 4,431 | 0.096 |
| 5 | a | 2,792 | 0.101 |
| 10 | or | 1,291 | 0.093 |
| 20 | plants | 699 | 0.101 |
| 50 | 2 | 408 | 0.147 |

The middle ranks fit well; the extremes deviate. "Plants" at rank 20 shows why stop lists should be adapted to the domain [05:28].

### Stemming
We use an algorithmic plural stemmer, extending the suffix-s idea [05:33]: "orchids" → "orchid", "berries" → "berry". Its limits include:

- **False negatives:** "climbing" (9 records) and "climber" (1) remain different terms.
- **Non-words:** "species" → "specy". This is not a word, but it is applied consistently to queries and documents.

Porter would stem more aggressively; Krovetz has fewer false positives but more false negatives [05:37].

### Document representation
Each document is a *bag of words*; word order is ignored. Common names and normalised attributes are repeated three times and scientific names twice to boost them. Repetition raises term frequency, but also document length, and BM25 reduces the benefit of each further occurrence.

## 5. Ranking with BM25

The course develops BM25 by improving a simple vector space model in stages:

| Step | Idea | Reference |
|---|---|---|
| Bit vector | Count matched query words | [03:21] |
| TF | Repeated words deserve credit | [03:28] |
| IDF | Rare words deserve more credit | [03:31] |
| BM25 TF | Repetition has diminishing returns | [03:38] |
| Length normalisation | Avoid favouring long documents | [03:43] |

The course also presents BM25 in the classic probabilistic family [04:3]. Our implementation computes:

**score(q, d) = Σ idf(w) · c(w,d)(k+1) / ( c(w,d) + k(1 − b + b·|d|/avdl) )**

with k = 1.5, b = 0.75 and avdl = 195.8 tokens. Two details differ from the slides. The length normaliser is placed inside the TF component, and IDF is **log((N − df + 0.5)/(df + 0.5))** rather than log((M + 1)/df).

### Worked example: "pink orchid"
The top result, Roundleaf Orchid, has |d| = 33. Therefore:

K = 1.5 × (0.25 + 0.75 × 33/195.8) = **0.565**

| Word | df | idf | c(w,d) | TF component | Contribution |
|---|---|---|---|---|---|
| pink | 159 | 1.018 | 4 | 4 × 2.5 / 4.565 = 2.191 | 2.23 |
| orchid | 23 | 3.202 | 7 | 7 × 2.5 / 7.565 = 2.313 | 7.41 |
| **Score** | | | | | **9.64** |

The TF components are similar because both are near the upper bound k + 1 = 2.5. The difference comes mainly from IDF: "orchid" is rarer and more discriminating. The short document also helps, because K is small. This is a side effect to watch: this record's description is one of the generated, short ones.

### A weakness in the IDF
The formula becomes negative when a word occurs in more than half of the documents. The library then replaces it by 0.25 × the average IDF, here **1.277**.

| Word | df (of 600) | idf used |
|---|---|---|
| flower | 557 | 1.277 (floor) |
| plant | 437 | 1.277 (floor) |
| bloom | 282 | 0.120 |
| winter | 237 | 0.426 |
| pink | 159 | 1.018 |

Thus "flower", present in 93% of records, received *more* weight than "winter" or "pink". This contradicts the principle that IDF should penalise popular terms [03:32]. It helps explain the poor early ranking for "winter flowers". Our query processing hides the problem by dropping generic words when others remain. The slides' IDF, log(601/557) ≈ 0.08, would address it directly and would be a good choice for our own index.

## 6. Query processing

Queries are tokenised and stemmed like documents. Generic words ("flower", "bloom", "plant" and variants) are then dropped if more specific words remain, and "fall" and "autumn" are expanded to each other. The second step is a small, manual form of *query expansion*.

| Query | Results before | Results now |
|---|---|---|
| winter flowers | 572 | 237 |
| fall flowers | 564 | 320 |

Fewer results do not prove better effectiveness; that requires relevance judgements. Matching remains a disjunction: "pink orchid" returns all 166 records containing either word, although only 16 contain both. Records containing both tend to rank higher, but the long tail can be weakly relevant. Negation, phrases and misspellings are unsupported: "lavendar" returns nothing.

## 7. Index structure and efficiency

The indexed vocabulary has 7,444 terms. A full term–document matrix would have 4,466,400 cells, of which only 74,656 (1.7%) are non-zero. This sparsity is why an inverted index is effective [06:13].

At present, `rank_bm25` checks every document for every query term. The planned index will store, for example:

`orchid → [(doc 12, 7), (doc 40, 3), …]` (illustrative values)

Scoring will read only the postings of query terms and add contributions to score accumulators [06:26]. Counts are enough for BM25; positions would also support proximity [06:18, 06:19].

A local check gave a median of about 40 ms per search. This includes filtering, facet counts and snippets, and covers only three repeated queries. Speed is acceptable for 600 records; effectiveness matters more to users [09:5]. The lectures present Lucene/Solr for practical work [06:28]; we use a smaller pipeline so that ranking and feedback can be examined and extended directly.

## 8. Relevance feedback (planned)

The ✓/✗ buttons represent *explicit* feedback, as opposed to pseudo or implicit feedback [07:3]. They do not yet change the ranking. In the vector space model, Rocchio moves the query towards relevant documents [07:12]:

**q′ = α q + β · mean(relevant) − γ · mean(non-relevant)**

Typical values are α = 8, β = 16, γ = 4 [07:13]. We plan the practical version without the negative term [07:14].

**Toy example** over (pink, orchid, summer): let q = (1, 1, 0), and let the user approve documents (1, 2, 1) and (1, 0, 1). Their mean is (1, 1, 1), so:

q′ = 8 · (1, 1, 0) + 16 · (1, 1, 1) = **(24, 24, 16)**

"Summer" enters the query (*expansion*) and the original weights change (*modification*). We will keep only the strongest expansion terms and a high original weight to avoid over-fitting [07:14]. Records marked ✗ will be removed from the results: negative feedback changes the list without entering the query vector.

Rocchio needs weighted queries, but `rank_bm25` accepts only a list of words. Our own index will therefore use BM25 document weights and a dot product with q′.

## 9. Evaluation (planned)

Three different things can be measured [09:4]: efficiency, effectiveness and usability.

| | System evaluation | User evaluation |
|---|---|---|
| Needs | Documents, queries, relevance judgements | Participants and tasks |
| Measures | P@k, MAP, MRR, nDCG | Time, queries, success, SUS |
| In this project | Not required; no judgements exist | Required with three classmates |

**Aim:** evaluate the effect of feedback on search effort. **Baseline:** feedback off. **Experimental:** feedback on, with nothing else changed [10:23].

**Hypothesis:** participants need fewer queries to find five suitable plants with feedback on. This follows the lecture's preference for measurable claims [10:19].

**Design:** within-groups, with different but comparable decision, background and fact tasks [10:26]. The lecture's Latin square uses four subjects and tasks [10:25]; with three, we rotate tasks and system order as evenly as possible.

**Data:** time, number of queries and suitable plants found, plus Likert items, SUS and comments. A pilot will test the procedure [10:34]. Results will be descriptive, because three participants cannot support statistical claims. Logging is not yet built.

## 10. Conclusions

The project implements the chain from acquisition to ranked results, combining Boolean filters with BM25. Examining it through the course highlights four priorities:

1. **Complete the feedback loop** with Rocchio over weighted queries.
2. **Build an inverted index** with an IDF that penalises common terms.
3. **Widen the sample**, because ranking cannot compensate for missing documents.
4. **Evaluate with users**, because text retrieval is an empirically defined problem: one method cannot be mathematically proven better than another [02:28].

## Lecture files used

00 Overview · 01 Introduction · 02 Text access · 03 Retrieval models 1 · 04 Probabilistic models · 05–06 Implementation · 07 Feedback · 09 System evaluation · 10 User evaluation. The lectures are based mainly on C. X. Zhai and S. Massung, *Text Data Management and Analysis*, ACM, 2016. Formula details in section 5 come from the installed `rank_bm25` source code.

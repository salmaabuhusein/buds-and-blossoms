"""Inverted index with field weights, BM25 scoring over weighted queries, and Rocchio feedback."""
import math
from collections import Counter, defaultdict

K1, B = 1.5, 0.75
ALPHA, BETA, GAMMA = 8, 16, 4  # Rocchio weights: original query, relevant and non-relevant documents
EXPANSION_TERMS = 10  # only the strongest new terms enter the query
MIN_DF = 3            # rarer terms mostly identify the marked plants themselves
MIN_SHARED = 2        # documents of a feedback set that must contain a new term


class InvertedIndex:
    def __init__(self, docs, field_weights, feedback_fields, phrase_fields=None):
        """docs: one {field: [token, ...]} per document. Only feedback_fields supply expansion terms,
        and only phrase_fields (default: all) are indexed as word pairs."""
        self.n = len(docs)
        self.postings = defaultdict(list)  # term -> [(doc, weighted term frequency), ...]
        self.bigrams = defaultdict(list)   # (term, next term) -> [(doc, weighted frequency), ...]
        self.forward = []                  # doc -> {term: weighted term frequency}, for feedback
        self.expandable = []               # doc -> terms that feedback may add to a query
        self.lengths = []
        for i, fields in enumerate(docs):
            tf = Counter()
            for field, tokens in fields.items():
                for t in tokens:
                    tf[t] += field_weights[field]
            self.forward.append(tf)
            self.expandable.append({t for f in feedback_fields for t in fields[f]})
            self.lengths.append(sum(tf.values()))
            for t, f in tf.items():
                self.postings[t].append((i, f))
            pairs = Counter()  # pairs never span two fields
            for field, tokens in fields.items():
                if phrase_fields is not None and field not in phrase_fields:
                    continue
                for pair in zip(tokens, tokens[1:]):
                    pairs[pair] += field_weights[field]
            for pair, f in pairs.items():
                self.bigrams[pair].append((i, f))
        self.avgdl = sum(self.lengths) / self.n if self.n else 0
        self.idf = {t: math.log((self.n + 1) / len(p)) for t, p in self.postings.items()}
        self.bigram_idf = {p: math.log((self.n + 1) / len(d)) for p, d in self.bigrams.items()}

    def bm25(self, idf, doc, tf):
        norm = K1 * (1 - B + B * self.lengths[doc] / self.avgdl)
        return idf * tf * (K1 + 1) / (tf + norm)

    def weight(self, term, doc, tf):
        """BM25 weight of a term in a document."""
        return self.bm25(self.idf[term], doc, tf)

    def phrase_score(self, pairs):
        """BM25 over word pairs: each pair is scored like a term, with its own document frequency."""
        acc = defaultdict(float)
        for pair in pairs:
            for doc, tf in self.bigrams.get(pair, ()):
                acc[doc] += self.bm25(self.bigram_idf[pair], doc, tf)
        return dict(acc)

    def score(self, query):
        """Dot product of a {term: weight} query with the documents, reading only the query terms' postings."""
        acc = defaultdict(float)
        for term, qw in query.items():
            for doc, tf in self.postings.get(term, ()):
                acc[doc] += qw * self.weight(term, doc, tf)
        return dict(acc)

    def having(self, terms):
        """Documents that contain every one of the terms."""
        docs = None
        for t in terms:
            found = {doc for doc, _ in self.postings.get(t, ())}
            docs = found if docs is None else docs & found
        return docs or set()

    def coverage(self, concepts):
        """Fraction of the query's concepts (sets of synonyms) that each document contains."""
        acc = defaultdict(int)
        for terms in concepts:
            for doc in {d for t in terms for d, _ in self.postings.get(t, ())}:
                acc[doc] += 1
        return {d: c / len(concepts) for d, c in acc.items()}

    def centroid(self, docs, query):
        """Mean of the documents' unit-length vectors, over the query terms and their expandable terms.

        With several documents, a new term must occur in at least MIN_SHARED of them: terms of a single
        document mostly identify that plant (its name) rather than what the marked plants have in common.
        """
        acc, count = defaultdict(float), Counter()
        for doc in docs:
            vec = {t: self.weight(t, doc, tf) for t, tf in self.forward[doc].items()
                   if t in query or t in self.expandable[doc]}
            for t, w in unit(vec).items():
                acc[t] += w / len(docs)
                count[t] += 1
        need = min(MIN_SHARED, len(docs))
        return {t: w for t, w in acc.items() if t in query or count[t] >= need}

    def rocchio(self, query, relevant, nonrelevant=(), skip=lambda term: False):
        """q' = alpha * q + beta * mean(relevant) - gamma * mean(non-relevant), on unit-length vectors.

        Only the strongest new terms of the relevant centroid are added, and negative weights
        are set to zero. Returns the new query and the expansion terms, strongest first.
        """
        pos = self.centroid(relevant, query)
        neg = self.centroid(nonrelevant, query) if nonrelevant else {}
        gain = {t: BETA * w - GAMMA * neg.get(t, 0) for t, w in pos.items()}
        new = sorted((t for t in gain if t not in query and gain[t] > 0 and len(self.postings[t]) >= MIN_DF
                      and not skip(t)), key=lambda t: (-gain[t], t))[:EXPANSION_TERMS]
        out = {t: ALPHA * w for t, w in unit(query).items()}
        for t in query:
            out[t] = max(0.0, out[t] + gain.get(t, -GAMMA * neg.get(t, 0)))
        for t in new:
            out[t] = gain[t]
        return {t: w for t, w in out.items() if w > 0}, new


def unit(vec):
    norm = math.sqrt(sum(w * w for w in vec.values()))
    return {t: w / norm for t, w in vec.items()} if norm else {}

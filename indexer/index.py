"""Plant search: text processing, ranking with relevance feedback, facet counting and highlighted snippets."""
import hashlib
import html
import json
import re
from collections import Counter
from pathlib import Path

from indexer.inverted import InvertedIndex

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "plants.jsonl"

STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was were
which with will can may also into their they these those very often i me my we our you your he she him her
them what who whom when where why how all any both each more most other some such no nor not only own same
so than too just should would could if but because while about through during before after then once here
there do does did been being having""".split())
# words describing nearly every record, and filler words of typed questions:
# dropped from a query when more specific words remain
GENERIC = {"flower", "flowering", "bloom", "blooming", "plant", "something", "anything", "looking", "want",
           "need", "like", "nice", "pretty", "good", "grow", "growing", "kind", "type"}
SYNONYMS = {"fall": ["autumn"], "autumn": ["fall"]}  # season label vs. wording in descriptions
FACETS = {"colors": "colors", "seasons": "seasons", "sun": "sun", "type": "type", "source": "source"}


IRREGULAR = {"leaves": "leaf", "irises": "iris", "cacti": "cactus", "cactuses": "cactus", "crocuses": "crocus"}


def singular(t):
    """Light plural stemming (Harman's S-stemmer plus -es after ch/sh/ss/x/o)."""
    if t in IRREGULAR:
        return IRREGULAR[t]
    if len(t) <= 3 or t.endswith(("ss", "us", "is")):
        return t
    if len(t) > 4 and t.endswith("ies"):
        return t[:-3] + "y"
    if len(t) > 4 and t.endswith(("ches", "shes", "sses", "xes", "oes")):
        return t[:-2]
    return t[:-1] if t.endswith("s") else t


STEMMER = singular  # swapped by eval/relevance.py to compare stemmers


def stem(t):
    return STEMMER(t)


def tokenize(text):
    return [stem(t) for t in re.findall(r"[a-z0-9]+", (text or "").lower()) if t not in STOP]


def query_concepts(query):
    """Query-time processing on top of tokenize(): drop generic words, then group each word with its synonyms."""
    toks = tokenize(query)
    generic = {stem(g) for g in GENERIC}
    toks = [t for t in toks if t not in generic] or toks
    return list(dict.fromkeys(tuple(sorted([t] + synonyms(t))) for t in toks))


def synonyms(t):
    return [stem(s) for s in SYNONYMS.get(t, [])]


def query_terms(query):
    return [t for concept in query_concepts(query) for t in concept]


def query_phrases(query):
    """Adjacent word pairs of the query, as typed (generic words kept: "red flowers" is a useful phrase)."""
    toks = tokenize(query)
    return list(dict.fromkeys((a, b) for x, y in zip(toks, toks[1:])
                              for a in [x] + synonyms(x) for b in [y] + synonyms(y)))


FIELD_WEIGHTS = {"name": 3, "scientific": 2, "attributes": 3, "text": 1}
PHRASE_WEIGHT = 1.0  # weight of query word pairs found next to each other (bigrams), relative to single words
PHRASE_FIELDS = ("name", "scientific")  # in descriptions, pairs like "white flowers" outweighed the other query words
FEEDBACK_FIELDS = ("name", "scientific", "attributes")  # words from descriptions mostly add noise


def attribute_values(r):
    return r["colors"] + r["seasons"] + r["sun"] + [r["type"], r["family"]]


def doc_fields(r):
    return {
        "name": r["name"],
        "scientific": r["scientific_name"],
        "attributes": " ".join(attribute_values(r)),
        "text": r["description"] + " " + r["extra_text"],
    }


class PlantIndex:
    def __init__(self, path=DATA):
        self.docs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        for d in self.docs:  # row numbers change on every crawl; the URL does not
            d["id"] = hashlib.sha1(d["url"].encode()).hexdigest()[:12]
        self.by_id = {d["id"]: i for i, d in enumerate(self.docs)}
        fields = [doc_fields(d) for d in self.docs]
        self.index = InvertedIndex([{f: tokenize(s) for f, s in d.items()} for d in fields],
                                   FIELD_WEIGHTS, FEEDBACK_FIELDS, PHRASE_FIELDS)
        # most common spelling of each stem, to show expansion terms as real words
        spellings = {}
        for d in fields:
            for w in re.findall(r"[a-z0-9]+", " ".join(d.values()).lower()):
                spellings.setdefault(stem(w), Counter())[w] += 1
        self.spelling = {t: c.most_common(1)[0][0] for t, c in spellings.items()}

    # ---------- retrieval ----------
    def score(self, query, relevant=(), rejected=()):
        """Scores by document and the expansion terms; (None, []) when there is nothing to rank by."""
        concepts = query_concepts(query)
        weights = {t: 1.0 for c in concepts for t in c}
        new = []
        if relevant:
            generic = {stem(g) for g in GENERIC}
            weights, new = self.index.rocchio(weights, relevant, rejected,
                                              skip=lambda t: t in generic or len(t) < 3 or t.isdigit())
        if not weights:
            return None, []
        scores = self.index.score(weights)
        for d, s in self.index.phrase_score(query_phrases(query)).items():
            if d in scores:  # a bonus for records that contain the query words next to each other
                scores[d] += PHRASE_WEIGHT * s
        cov = self.index.coverage(concepts)
        values = self.expansion_values(new, relevant)
        if concepts:
            # with a query, feedback re-ranks the records matching it (and the ones marked relevant) but adds
            # no others; records matching more of the words the user typed come first
            scores = {d: s * (1 + cov.get(d, 0)) / 2 for d, s in scores.items() if d in cov or d in relevant}
        elif values:
            # browsing: the expansion is the whole query, so a record needs at least half of its values
            hits = Counter(d for terms in values.values() for d in self.index.having(terms))
            need = (len(values) + 1) // 2
            scores = {d: s for d, s in scores.items() if d in relevant or hits[d] >= need}
        return scores, list(values)

    def expansion_values(self, terms, relevant):
        """Expansion terms grouped as the user should read them, {label: [term, ...]}, strongest first.

        The index splits attribute values into words, so the terms taken from "Partial shade" of the marked
        plants form one value, shown whole, instead of "partial" and "shade".
        """
        values = {}
        for t in terms:
            found = Counter(v for i in relevant for v in attribute_values(self.docs[i])
                            if len(v.split()) > 1 and t in tokenize(v))
            label = found.most_common(1)[0][0].lower() if found else self.spelling.get(t, t)
            values.setdefault(label, []).append(t)
        return values

    @staticmethod
    def matches(d, filters):
        for key, field in FACETS.items():
            want = filters.get(key)
            if not want:
                continue
            val = d[field]
            vals = val if isinstance(val, list) else [val]
            if not set(want) & set(vals):
                return False
        z = filters.get("zone")
        if z:
            if d["zone_min"] is None or not (d["zone_min"] <= z <= d["zone_max"]):
                return False
        return True

    def facet_counts(self, ids, filters):
        """Count per facet value, applying every *other* facet's filter (standard faceted search)."""
        out = {}
        for key, field in FACETS.items():
            others = {k: v for k, v in filters.items() if k != key}
            c = Counter()
            for i in ids:
                d = self.docs[i]
                if not self.matches(d, others):
                    continue
                val = d[field]
                c.update(val if isinstance(val, list) else [val])
            out[key] = dict(c.most_common())
        return out

    def search(self, query="", filters=None, sort="relevance", relevant=(), rejected=(), page=1, page_size=None):
        """relevant / rejected: ids of records marked by the user; unknown ids are ignored.

        page (1-based) and page_size limit the returned results; total and facets always cover all hits.
        """
        filters = filters or {}
        relevant = list(dict.fromkeys(self.by_id[r] for r in relevant if r in self.by_id))
        rejected = {self.by_id[r] for r in rejected if r in self.by_id}
        scores, expansion = self.score(query, [i for i in relevant if i not in rejected], sorted(rejected))
        pool = [i for i in range(len(self.docs)) if i not in rejected and (scores is None or scores.get(i, 0) > 0)]
        facets = self.facet_counts(pool, filters)
        hits = [i for i in pool if self.matches(self.docs[i], filters)]
        if sort == "zone":  # hardiest first; records without a zone last
            hits.sort(key=lambda i: (self.docs[i]["zone_min"] or 99, self.docs[i]["name"].lower()))
        elif sort == "name" or scores is None:
            hits.sort(key=lambda i: self.docs[i]["name"].lower())
        else:
            hits.sort(key=lambda i: -scores[i])
        q = query_terms(query)
        total = len(hits)
        if page_size:
            pages = max(1, -(-total // page_size))
            page = min(max(1, page), pages)
            hits = hits[(page - 1) * page_size: page * page_size]
        results = []
        for i in hits:
            d = dict(self.docs[i])
            d["score"] = round(float(scores[i]), 2) if scores is not None else None
            d["snippet"] = snippet(d["description"] or d["extra_text"], q)
            d["name_html"] = highlight(html.escape(d["name"]), q)
            d.pop("extra_text", None)
            results.append(d)
        return {"total": total, "page": page if page_size else 1, "page_size": page_size or total,
                "results": results, "facets": facets, "expansion": expansion}


def highlight(escaped_text, qtoks):
    if not qtoks:
        return escaped_text
    terms = set(qtoks)

    def mark(m):
        w = m.group(0)  # HTML entities such as &quot; are matched whole and left alone
        return f"<mark>{w}</mark>" if w[0] != "&" and stem(w.lower()) in terms else w

    return re.sub(r"&#?\w+;|[A-Za-z0-9]+", mark, escaped_text)


def snippet(text, qtoks, max_chars=230):
    """Google-style: pick the sentence window with the most query-term hits, then highlight."""
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    sents = re.split(r"(?<=[.!?])\s+", text)
    best, best_hits = 0, -1
    for i, s in enumerate(sents):
        hits = len(set(tokenize(s)) & set(qtoks)) if qtoks else 0
        if hits > best_hits:
            best, best_hits = i, hits
    out = ""
    for s in sents[best:]:
        if len(out) + len(s) > max_chars and out:
            break
        out += (" " if out else "") + s
    if len(out) > max_chars:
        out = out[:max_chars].rsplit(" ", 1)[0] + "…"
    prefix = "… " if best > 0 else ""
    return prefix + highlight(html.escape(out), qtoks)

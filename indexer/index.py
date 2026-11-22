"""BM25 index over plant records with field boosting, facet counting and highlighted snippets."""
import html
import json
import re
from collections import Counter
from pathlib import Path

from rank_bm25 import BM25Okapi

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "plants.jsonl"

STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was were
which with will can may also into their they these those very often""".split())
FACETS = {"colors": "colors", "seasons": "seasons", "sun": "sun", "type": "type", "source": "source"}


def tokenize(text):
    toks = re.findall(r"[a-z0-9]+", (text or "").lower())
    out = []
    for t in toks:
        if t in STOP:
            continue
        # light stemming: plural / -ing forms
        for suf in ("ies", "es", "s"):
            if len(t) > 4 and t.endswith(suf) and not t.endswith("ss"):
                t = t[: -len(suf)] + ("y" if suf == "ies" else "")
                break
        out.append(t)
    return out


def doc_text(r):
    # repeat fields to boost them: name x3, scientific x2, normalized attributes x3, description x1
    attrs = " ".join(r["colors"] + r["seasons"] + r["sun"] + [r["type"], r["family"]])
    return " ".join([r["name"]] * 3 + [r["scientific_name"]] * 2 + [attrs] * 3 + [r["description"], r["extra_text"]])


class PlantIndex:
    def __init__(self, path=DATA):
        self.docs = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
        self.tokens = [tokenize(doc_text(d)) for d in self.docs]
        self.bm25 = BM25Okapi(self.tokens)

    # ---------- retrieval ----------
    def score(self, query):
        q = tokenize(query)
        if not q:
            return None
        return self.bm25.get_scores(q)

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

    def search(self, query="", filters=None, sort="relevance", scores=None):
        filters = filters or {}
        if scores is None:
            scores = self.score(query) if query.strip() else None
        if scores is not None:
            pool = [i for i in range(len(self.docs)) if scores[i] > 0]
        else:
            pool = list(range(len(self.docs)))
        facets = self.facet_counts(pool, filters)
        hits = [i for i in pool if self.matches(self.docs[i], filters)]
        if sort == "name" or scores is None:
            hits.sort(key=lambda i: self.docs[i]["name"].lower())
        elif sort == "zone":
            hits.sort(key=lambda i: (self.docs[i]["zone_min"] or 99, self.docs[i]["name"]))
        else:
            hits.sort(key=lambda i: -scores[i])
        q = tokenize(query)
        results = []
        for i in hits:
            d = dict(self.docs[i])
            d["score"] = round(float(scores[i]), 2) if scores is not None else None
            d["snippet"] = snippet(d["description"] or d["extra_text"], q)
            d["name_html"] = highlight(html.escape(d["name"]), q)
            d.pop("extra_text", None)
            results.append(d)
        return {"total": len(results), "results": results, "facets": facets}


def highlight(escaped_text, qtoks):
    if not qtoks:
        return escaped_text
    pat = re.compile(r"\b(" + "|".join(re.escape(t) for t in qtoks) + r")[a-z]*", re.I)
    return pat.sub(lambda m: f"<mark>{m.group(0)}</mark>", escaped_text)


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

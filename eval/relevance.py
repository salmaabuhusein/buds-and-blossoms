"""Offline check of ranking changes on test queries whose relevance is judged from the plant records.

    .venv/bin/python eval/relevance.py                 # current settings
    .venv/bin/python eval/relevance.py --compare       # stemmers, stop list, phrase weight, Rocchio gamma

Judgements come from the structured fields (colour, season, light, type) and description keywords, so they
are approximate: use the numbers to compare settings, not as a measure of real user satisfaction.
Porter needs `pip install nltk`, Krovetz `pip install krovetzstemmer`; both are optional.
"""
import argparse
import re
import statistics as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import indexer.index as N  # noqa: E402
import indexer.inverted as V  # noqa: E402


def has(d, field, value):
    return value in d[field] if isinstance(d[field], list) else d[field] == value


def text(d, pattern):
    return re.search(pattern, (d["name"] + " " + d["description"] + " " + d["extra_text"]).lower()) is not None


SHADE = lambda d: has(d, "sun", "Partial shade") or has(d, "sun", "Full shade")  # noqa: E731
QUERIES = [
    ("pink orchid", lambda d: has(d, "colors", "Pink") and has(d, "type", "Orchid")),
    ("white flowering shrub", lambda d: has(d, "colors", "White") and has(d, "type", "Shrub")),
    ("yellow spring bulbs", lambda d: has(d, "colors", "Yellow") and has(d, "seasons", "Spring") and has(d, "type", "Bulb")),
    ("red climbing vine", lambda d: has(d, "colors", "Red") and has(d, "type", "Vine")),
    ("blue flowers for shade", lambda d: has(d, "colors", "Blue") and SHADE(d)),
    ("purple autumn flowers", lambda d: has(d, "colors", "Purple") and has(d, "seasons", "Autumn")),
    ("winter flowering shrubs", lambda d: has(d, "seasons", "Winter") and has(d, "type", "Shrub")),
    ("fragrant white flowers", lambda d: has(d, "colors", "White") and text(d, r"fragran")),
    ("trees with white flowers", lambda d: has(d, "colors", "White") and has(d, "type", "Tree")),
    ("drought tolerant yellow flowers", lambda d: has(d, "colors", "Yellow") and text(d, r"drought")),
    ("orange annuals", lambda d: has(d, "colors", "Orange") and has(d, "type", "Annual")),
    ("plants that attract butterflies", lambda d: text(d, r"butterfl")),
    ("shade loving perennials", lambda d: SHADE(d) and has(d, "type", "Herbaceous perennial")),
    ("something pink for winter", lambda d: has(d, "colors", "Pink") and has(d, "seasons", "Winter")),
    ("ornamental grasses", lambda d: has(d, "type", "Grass")),
    ("evergreen shrub", lambda d: has(d, "type", "Shrub") and text(d, r"evergreen")),
    ("red flowers for hummingbirds", lambda d: has(d, "colors", "Red") and text(d, r"hummingbird")),
    ("spring blooming trees", lambda d: has(d, "seasons", "Spring") and has(d, "type", "Tree")),
    ("groundcover for shade", lambda d: SHADE(d) and text(d, r"ground ?cover")),
    ("i want a purple flower that grows in full sun", lambda d: has(d, "colors", "Purple") and has(d, "sun", "Full sun")),
]


# Feedback tasks: a vague typed query and the more specific need the user only recognises in the results.
P = lambda f, v: (lambda d: has(d, f, v))  # noqa: E731
ALL = lambda *fs: (lambda d: all(f(d) for f in fs))  # noqa: E731
FEEDBACK_TASKS = [
    ("pink", ALL(P("colors", "Pink"), P("type", "Orchid"))),
    ("pink flowers", ALL(P("colors", "Pink"), P("type", "Shrub"))),
    ("white shrub", ALL(P("colors", "White"), P("type", "Shrub"), P("seasons", "Spring"))),
    ("yellow", ALL(P("colors", "Yellow"), P("type", "Bulb"))),
    ("blue flowers", ALL(P("colors", "Blue"), SHADE)),
    ("purple", ALL(P("colors", "Purple"), P("seasons", "Autumn"))),
    ("winter", ALL(P("seasons", "Winter"), P("type", "Shrub"))),
    ("fragrant", ALL(P("colors", "White"), lambda d: text(d, r"fragran"))),
    ("tree", ALL(P("colors", "White"), P("type", "Tree"))),
    ("drought tolerant", ALL(P("colors", "Yellow"), lambda d: text(d, r"drought"))),
    ("annual", ALL(P("colors", "Orange"), P("type", "Annual"))),
    ("butterflies", ALL(P("colors", "Purple"), lambda d: text(d, r"butterfl"))),
    ("shade", ALL(P("type", "Herbaceous perennial"), P("sun", "Full shade"))),
    ("red", ALL(P("colors", "Red"), lambda d: text(d, r"hummingbird"))),
    ("vine", ALL(P("type", "Vine"), P("seasons", "Summer"))),
    ("spring trees", ALL(P("seasons", "Spring"), P("type", "Tree"), P("colors", "White"))),
    ("evergreen", ALL(P("type", "Shrub"), lambda d: text(d, r"evergreen"), P("colors", "White"))),
    ("grass", ALL(P("type", "Grass"), P("sun", "Full sun"))),
    ("orchid", ALL(P("type", "Orchid"), P("colors", "Purple"))),
    ("autumn", ALL(P("seasons", "Autumn"), P("colors", "Yellow"), P("type", "Herbaceous perennial"))),
]


def stemmers():
    out = {"plural (S-stemmer)": N.singular, "none": lambda t: t}
    try:
        from nltk.stem import PorterStemmer
        out["Porter"] = PorterStemmer().stem
    except ImportError:
        pass
    try:
        import krovetzstemmer
        out["Krovetz"] = krovetzstemmer.Stemmer().stem
    except ImportError:
        pass
    return out


def average_precision(ranked, rel, total):
    hits, s = 0, 0.0
    for k, ok in enumerate(map(rel, ranked), 1):
        if ok:
            hits += 1
            s += hits / k
    return s / total if total else 0.0


def evaluate(index):
    """Mean P@10 and MAP over the test queries, before feedback."""
    p10, aps = [], []
    for q, rel in QUERIES:
        docs = [index.docs[index.by_id[r["id"]]] for r in index.search(q)["results"]]
        total = sum(map(rel, index.docs))
        p10.append(sum(map(rel, docs[:10])) / 10)
        aps.append(average_precision(docs, rel, total))
    return st.mean(p10), st.mean(aps)


def evaluate_feedback(index):
    """Simulated user on FEEDBACK_TASKS: marks up to 3 relevant plants in the top 10 with a tick and every
    other one with a cross. Tasks with no relevant plant in the top 10 are skipped.

    Precision is measured on the next 10 plants the user has not seen yet (residual collection).
    """
    off, on = [], []
    for q, rel in FEEDBACK_TASKS:
        first = index.search(q)["results"]
        raw = [index.docs[index.by_id[r["id"]]] for r in first]
        good = [r["id"] for r, d in zip(first[:10], raw) if rel(d)][:3]
        bad = [r["id"] for r, d in zip(first[:10], raw) if not rel(d)]
        if not good:
            continue
        seen = {r["id"] for r in first[:10]}
        unseen = lambda res: [index.docs[index.by_id[r["id"]]] for r in res if r["id"] not in seen][:10]  # noqa: E731
        off.append(sum(map(rel, unseen(first))) / 10)
        on.append(sum(map(rel, unseen(index.search(q, relevant=good, rejected=bad)["results"]))) / 10)
    return len(on), st.mean(off), st.mean(on)


def known_item(index):
    """Search each plant by its common name (two words or more): mean reciprocal rank, and how often it comes first."""
    rr = []
    for d in index.docs:
        if len(re.findall(r"[A-Za-z]+", d["name"])) < 2:
            continue
        ids = [r["id"] for r in index.search(d["name"].lower())["results"]]
        rr.append(1 / (ids.index(d["id"]) + 1) if d["id"] in ids else 0)
    return st.mean(rr), sum(r == 1 for r in rr), len(rr)


def report(label, index, feedback=True):
    p10, ap = evaluate(index)
    mrr, first, n = known_item(index)
    line = f"{label:<34} P@10 {p10:.3f}  MAP {ap:.3f}  | names: MRR {mrr:.3f}, first {first}/{n}"
    if feedback:
        n, off, on = evaluate_feedback(index)
        line += f"  | feedback ({n} tasks): P@10 of unseen {off:.3f} -> {on:.3f}"
    print(line)


def compare():
    """Changes one setting at a time; everything else stays at the current value."""
    print("Stemmer")
    default = N.STEMMER
    for name, fn in stemmers().items():
        N.STEMMER = fn
        report(f"  {name}", N.PlantIndex(), feedback=False)
    N.STEMMER = default

    print("Stop list")
    default = N.STOP, N.GENERIC
    N.STOP, N.GENERIC = OLD_STOP, OLD_GENERIC
    report("  original", N.PlantIndex(), feedback=False)
    N.STOP, N.GENERIC = default
    report("  extended", N.PlantIndex(), feedback=False)

    print("Phrases (bigrams): fields, weight")
    default = N.PHRASE_FIELDS, N.PHRASE_WEIGHT
    for fields in (None, ("name", "scientific")):
        N.PHRASE_FIELDS = fields
        index = N.PlantIndex()
        for w in (0, 1, 2):
            N.PHRASE_WEIGHT = w
            report(f"  {'all' if fields is None else '+'.join(fields)}, {w}", index, feedback=False)
    N.PHRASE_FIELDS, N.PHRASE_WEIGHT = default

    print("Rocchio: new terms shared by n marked plants, gamma")
    index = N.PlantIndex()
    default = V.MIN_SHARED, V.GAMMA
    for shared in (1, 2):
        for g in (0, 4):
            V.MIN_SHARED, V.GAMMA = shared, g
            n, off, on = evaluate_feedback(index)
            print(f"  shared {shared}, gamma {g}: {n} tasks, P@10 of unseen plants {off:.3f} -> {on:.3f}")
    V.MIN_SHARED, V.GAMMA = default


OLD_STOP = set("""a an and are as at be by for from has have in is it its of on or that the this to was were
which with will can may also into their they these those very often""".split())
OLD_GENERIC = {"flower", "flowering", "bloom", "blooming", "plant"}

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--compare", action="store_true")
    ap.add_argument("--per-query", action="store_true")
    args = ap.parse_args()
    if args.compare:
        compare()
    else:
        index = N.PlantIndex()
        report("current settings", index)
        if args.per_query:
            for q, rel in QUERIES:
                docs = [index.docs[index.by_id[r["id"]]] for r in index.search(q)["results"]]
                print(f"  {q:<48} P@10 {sum(map(rel, docs[:10])) / 10:.1f}  relevant {sum(map(rel, index.docs))}")

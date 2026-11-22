"""Map each source's raw vocabulary onto one shared schema."""
import re

COLORS = ["White", "Yellow", "Orange", "Red", "Pink", "Purple", "Blue", "Green"]
COLOR_WORDS = {
    "White": ["white", "cream", "ivory"],
    "Yellow": ["yellow", "gold", "golden"],
    "Orange": ["orange", "apricot", "salmon", "peach"],
    "Red": ["red", "scarlet", "crimson", "burgundy", "maroon"],
    "Pink": ["pink", "rose", "magenta", "fuchsia"],
    "Purple": ["purple", "violet", "lavender", "lilac", "mauve", "plum"],
    "Blue": ["blue"],
    "Green": ["green", "chartreuse"],
}
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
MONTH_SEASON = {
    "jan": "Winter", "feb": "Winter", "mar": "Spring", "apr": "Spring", "may": "Spring",
    "jun": "Summer", "jul": "Summer", "aug": "Summer", "sep": "Autumn", "oct": "Autumn",
    "nov": "Autumn", "dec": "Winter",
}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
TYPES = [  # (label, keywords) — first match wins
    ("Orchid", ["orchid"]),
    ("Succulent", ["succulent", "cactus", "cacti"]),
    ("Bulb", ["bulb", "corm", "tuber"]),
    ("Vine", ["vine", "climber", "climbing"]),
    ("Tree", ["tree"]),
    ("Shrub", ["shrub", "subshrub", "evergreen", "deciduous"]),
    ("Grass", ["grass", "sedge", "rush"]),
    ("Fern", ["fern"]),
    ("Annual", ["annual", "biennial"]),
    ("Herbaceous perennial", ["perennial", "herb", "forb", "wildflower"]),
]


def words(s):
    return (s or "").lower()


def norm_colors(raw):
    t = words(raw)
    return [c for c in COLORS if any(re.search(rf"\b{w}", t) for w in COLOR_WORDS[c])]


def norm_seasons(raw):
    t = words(raw)
    out = set()
    for s in SEASONS:
        if s.lower() in t:
            out.add(s)
    if "fall" in t:
        out.add("Autumn")
    # month ranges: "May to July" / "Jun, Jul, Aug"
    found = [m for m in MONTHS if re.search(rf"\b{m}", t)]
    rng = re.search(r"\b(" + "|".join(MONTHS) + r")[a-z]*\s+(?:to|-|–)\s+(" + "|".join(MONTHS) + r")", t)
    if rng:
        a, b = MONTHS.index(rng.group(1)), MONTHS.index(rng.group(2))
        idx = range(a, b + 1) if a <= b else list(range(a, 12)) + list(range(0, b + 1))
        found += [MONTHS[i] for i in idx]
    out |= {MONTH_SEASON[m] for m in found}
    return [s for s in SEASONS if s in out]


def norm_sun(raw):
    t = words(raw)
    out = set()
    if re.search(r"full sun|\bsun\b|6 or more hours", t):
        out.add("Full sun")
    if re.search(r"part|dappled|filtered|2-6 hours|semi", t):
        out.add("Partial shade")
    if re.search(r"full shade|deep shade|\bshade\b(?! through)|less than 2 hours", t) and "part" not in t:
        out.add("Full shade")
    if "sun to part shade" in t or "sun to shade" in t:
        out |= {"Full sun", "Partial shade"}
    if "part shade to full shade" in t or "to full shade" in t:
        out.add("Full shade")
    return [s for s in ["Full sun", "Partial shade", "Full shade"] if s in out]


def norm_zones(raw):
    nums = [int(n) for n in re.findall(r"\b(\d{1,2})[ab]?\b", raw or "") if 1 <= int(n) <= 13]
    return (min(nums), max(nums)) if nums else (None, None)


def norm_type(raw):
    t = words(raw)
    for label, kws in TYPES:
        if any(k in t for k in kws):
            return label
    return "Other"


def normalize(r):
    if not r.get("name") or not r.get("scientific_name"):
        return None
    zmin, zmax = norm_zones(r.get("zone_raw"))
    colors = norm_colors(r.get("color_raw"))
    if not colors:  # fall back to scanning the flower description
        colors = norm_colors(r.get("extra_text", "")[:300])
    ptype = "Orchid" if r.get("family") == "Orchidaceae" else norm_type(r.get("type_raw"))
    name = r["name"].strip()
    if name.islower():
        name = " ".join(w[:1].upper() + w[1:] for w in name.split())  # str.title() breaks "monk's"
    colors_l = norm_colors(r.get("color_raw")) or norm_colors(r.get("extra_text", "")[:300])
    seasons_l = norm_seasons(r.get("season_raw"))
    sun_l = norm_sun(r.get("sun_raw"))
    desc = (r.get("description") or "").strip() or (r.get("extra_text") or "").strip()
    if not desc:  # last resort: a readable summary built from the structured fields
        art = "An" if ptype[0].lower() in "aeiou" else "A"
        bits = [f"{art} {ptype.lower()} in the {r.get('family') or 'unknown'} family"]
        if colors_l:
            bits.append(f"with {' and '.join(c.lower() for c in colors_l)} flowers")
        if seasons_l:
            bits.append(f"blooming in {' and '.join(s.lower() for s in seasons_l)}")
        desc = " ".join(bits) + (f". Prefers {', '.join(s.lower() for s in sun_l)}." if sun_l else ".")
    r = {**r, "description": desc}
    return {
        "name": name,
        "scientific_name": r["scientific_name"],
        "source": r["source"],
        "url": r["url"],
        "image": r.get("image", ""),
        "family": r.get("family", ""),
        "type": ptype,
        "description": r.get("description", ""),
        "extra_text": r.get("extra_text", ""),
        "colors": colors,
        "seasons": norm_seasons(r.get("season_raw")),
        "sun": norm_sun(r.get("sun_raw")),
        "zone_min": zmin,
        "zone_max": zmax,
    }

"""Map each source's raw vocabulary onto one shared schema."""
import re

COLORS = ["White", "Yellow", "Orange", "Red", "Pink", "Purple", "Blue", "Green"]
COLOR_WORDS = {
    "White": ["white", "whitish", "cream", "creamy", "ivory"],
    "Yellow": ["yellow", "yellowish", "gold", "golden"],
    "Orange": ["orange", "orangish", "apricot", "salmon", "peach"],
    "Red": ["red", "reddish", "scarlet", "crimson", "burgundy", "maroon"],
    "Pink": ["pink", "pinkish", "rose", "rosy", "magenta", "fuchsia"],
    "Purple": ["purple", "purplish", "violet", "lavender", "lilac", "mauve", "plum"],
    "Blue": ["blue", "bluish"],
    "Green": ["green", "greenish", "chartreuse"],
}
SEASONS = ["Spring", "Summer", "Autumn", "Winter"]
MONTH_SEASON = {
    "jan": "Winter", "feb": "Winter", "mar": "Spring", "apr": "Spring", "may": "Spring",
    "jun": "Summer", "jul": "Summer", "aug": "Summer", "sep": "Autumn", "oct": "Autumn",
    "nov": "Autumn", "dec": "Winter",
}
MONTHS = ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"]
SEASON_MONTHS = {"spring": [2, 3, 4], "summer": [5, 6, 7], "fall": [8, 9, 10], "autumn": [8, 9, 10],
                 "winter": [11, 0, 1]}
_MONTH = (r"jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|july?|aug(?:ust)?|"
          r"sept?(?:ember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?")
_SEASON = "|".join(SEASON_MONTHS)
_WHEN = rf"(?:(early|mid|late)[ -]+)?\b({_MONTH}|{_SEASON})\b"
RANGE = re.compile(rf"{_WHEN}\s*(?:to|through|-|–)\s*{_WHEN}")
TYPES = [  # (label, keywords) — first match wins
    ("Orchid", ["orchid"]),
    ("Succulent", ["succulent", "cactus", "cacti"]),
    ("Bulb", ["bulb", "corm", "tuber"]),
    ("Vine", ["vine", "climber", "climbing"]),
    ("Tree", ["tree", "palm", "cycad"]),
    ("Shrub", ["shrub", "subshrub", "broadleaf evergreen", "needled evergreen", "rose"]),
    ("Grass", ["grass", "sedge", "rush"]),
    ("Fern", ["fern"]),
    ("Annual", ["annual", "biennial"]),
    ("Herbaceous perennial", ["perennial", "herb", "herbaceous", "forb", "wildflower"]),
    ("Fruit", ["fruit"]),  # Missouri's type for fruit crops; last, so it only catches records with no other type
]


def words(s):
    return (s or "").lower()


def norm_colors(raw):
    t = words(raw)
    return [c for c in COLORS if any(re.search(rf"\b{w}s?\b", t) for w in COLOR_WORDS[c])]


def _months(word, qualifier=""):
    """Month indices covered by a month or season name; "early"/"mid"/"late" pick one month of a season."""
    key = word[:3]
    if key in MONTHS:
        return [MONTHS.index(key)]
    months = SEASON_MONTHS[word]
    q = (qualifier or "").strip(" -")
    return [months[("early", "mid", "late").index(q)]] if q else months


def norm_seasons(raw):
    t = words(raw)
    out = {"Autumn" if s == "fall" else s.capitalize() for s in re.findall(rf"\b(?:{_SEASON})\b", t)}
    out |= {MONTH_SEASON[m[:3]] for m in re.findall(rf"\b(?:{_MONTH})\b", t)}
    # ranges of months and/or seasons, wrapping around the year: "May to July", "Late Fall to May"
    for q1, w1, q2, w2 in RANGE.findall(t):
        a, b = _months(w1, q1)[0], _months(w2, q2)[-1]
        out |= {MONTH_SEASON[MONTHS[(a + i) % 12]] for i in range((b - a) % 12 + 1)}
    return [s for s in SEASONS if s in out]


def norm_sun(raw):
    t = words(raw)
    out = set()
    if re.search(r"full sun|\bsun\b|6 or more hours", t):
        out.add("Full sun")
    if re.search(r"part|dappled|filtered|2-6 hours|semi", t):
        out.add("Partial shade")
    no_part = re.sub(r"(?:part(?:ial)?|semi)[ -]shade", "", t)  # "Part Shade, Shade" lists both
    if re.search(r"full shade|deep shade|\bshade\b(?! through)|less than 2 hours", no_part):
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
        if any(re.search(rf"\b{k}(?:s|es)?\b", t) for k in kws):
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
    seasons = norm_seasons(r.get("season_raw"))
    sun = norm_sun(r.get("sun_raw"))
    desc = (r.get("description") or "").strip() or (r.get("extra_text") or "").strip()
    if not desc:  # last resort: a readable summary built from the structured fields
        art = "An" if ptype[0].lower() in "aeiou" else "A"
        bits = [f"{art} {ptype.lower()} in the {r.get('family') or 'unknown'} family"]
        if colors:
            bits.append(f"with {' and '.join(c.lower() for c in colors)} flowers")
        if seasons:
            bits.append(f"blooming in {' and '.join(s.lower() for s in seasons)}")
        desc = " ".join(bits) + (f". Prefers {', '.join(s.lower() for s in sun)}." if sun else ".")
    return {
        "name": name,
        "scientific_name": r["scientific_name"],
        "source": r["source"],
        "url": r["url"],
        "image": r.get("image", ""),
        "family": r.get("family", ""),
        "type": ptype,
        "description": desc,
        "extra_text": r.get("extra_text", ""),
        "colors": colors,
        "seasons": seasons,
        "sun": sun,
        "zone_min": zmin,
        "zone_max": zmax,
    }

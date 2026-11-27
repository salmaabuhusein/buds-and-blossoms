"""Polite crawler for three plant databases -> data/plants.jsonl (one normalized record per line).

Sources:
  mbg  Missouri Botanical Garden Plant Finder   (A-Z list pages)
  ncsu NC State Extension Plant Toolbox          (sitemap.xml)
  wf   Lady Bird Johnson Wildflower Center       (search by plant family)

Usage: python crawler/crawl.py [--per-source 500] [--delay 1.0] [--only mbg,ncsu,wf]
Raw HTML is cached in data/raw/ so re-runs don't re-download.
"""
import argparse, hashlib, json, random, re, sys, time
import urllib.robotparser
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent))
from normalize import normalize  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "plants.jsonl"
UA = "Mozilla/5.0 (compatible; BudsAndBlossoms-student-IR-project/1.0)"
session = requests.Session()
session.headers["User-Agent"] = UA
DELAY = 1.0


_robots = {}


def allowed(url):
    """Respect robots.txt (a missing robots.txt means everything is allowed)."""
    p = urlparse(url)
    host = f"{p.scheme}://{p.netloc}"
    if host not in _robots:
        rp = urllib.robotparser.RobotFileParser()
        try:
            r = session.get(host + "/robots.txt", timeout=30)
            rp.parse(r.text.splitlines() if r.status_code == 200 else [])
        except requests.RequestException:
            rp.parse([])
        _robots[host] = rp
    return _robots[host].can_fetch(UA, url)


def fetch(url):
    RAW.mkdir(parents=True, exist_ok=True)
    f = RAW / (hashlib.md5(url.encode()).hexdigest() + ".html")
    if f.exists():
        return f.read_text(encoding="utf-8", errors="ignore")
    if not allowed(url):
        print("  ! disallowed by robots.txt", url)
        return None
    time.sleep(DELAY)
    # hard wall-clock deadline: requests' timeout only limits gaps between bytes,
    # so a slowly trickling response could otherwise block forever
    deadline = time.time() + (150 if "ListResults" in url else 60)
    try:
        with session.get(url, timeout=(10, 60), stream=True) as r:
            if r.status_code != 200:
                print("  !", r.status_code, url)
                return None
            chunks = []
            for chunk in r.iter_content(65536):
                chunks.append(chunk)
                if time.time() > deadline:
                    raise requests.Timeout("wall-clock deadline exceeded")
            text = b"".join(chunks).decode(r.encoding or "utf-8", errors="ignore")
    except requests.RequestException as e:
        print("  ! error", url, e)
        return None
    f.write_text(text, encoding="utf-8")
    return text


def clean(s):
    return re.sub(r"\s+", " ", s or "").strip()


def spread(urls):
    """All candidate pages in a fixed random order: the crawl stops after --per-source records, so any prefix
    must be a sample of the whole site rather than its first letters. The fixed seed keeps rebuilds offline."""
    urls = list(dict.fromkeys(urls))
    random.Random(13).shuffle(urls)
    return urls


# ---------------- Missouri Botanical Garden ----------------
MBG = "https://plantfinder.mobot.org/"


def mbg_urls():
    urls = []
    for letter in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        html = fetch(f"{MBG}PlantFinderListResults.aspx?letter={letter}")
        if html:
            urls += [f"{MBG}PlantFinderDetails.aspx?taxonid={i}"
                     for i in re.findall(r"PlantFinderDetails\.aspx\?taxonid=(\d+)", html)]
    print(f"  {len(set(urls))} candidate pages")
    return spread(urls)


def mbg_parse(url, html):
    s = BeautifulSoup(html, "lxml")
    text = s.get_text("\n", strip=True)
    fields = {}
    for key in ["Common Name", "Type", "Family", "Zone", "Bloom Time", "Bloom Description", "Sun", "Height"]:
        m = re.search(rf"^{key}:\s*(.+)$", text, re.M)
        if m:
            fields[key] = clean(m.group(1))
    if "Common Name" not in fields:
        return None
    title = s.find(id=re.compile("lblTitle$"))
    sci = clean(title.get_text(" ")) if title else ""
    if not sci:
        m = re.search(r"Gardening Help Search\n(.+?)\nBack to Previous Page", text, re.S)
        sci = clean(m.group(1)) if m else ""
    desc = ""
    m = re.search(r"Noteworthy Characteristics\n(.+?)(?:\nProblems\n|\nGarden Uses\n|$)", text, re.S)
    if m:
        desc = clean(m.group(1))
    culture = ""
    m = re.search(r"\nCulture\n(.+?)\nNoteworthy Characteristics", text, re.S)
    if m:
        culture = clean(m.group(1))
    img = re.search(r'src="(https://images\.mobot\.org/[^"]+/small240/[^"]+)"', html)
    if not img:  # some pages only link 100px thumbnails; the 240px version exists at the same path
        img = re.search(r'"(https://images\.mobot\.org/[^"]+/thumbnail100/[^"]+)"', html)
    image = img.group(1).replace("/thumbnail100/", "/small240/") if img else ""
    return {
        "source": "Missouri Botanical Garden", "url": url,
        "image": image,
        "name": fields["Common Name"].split(",")[0], "scientific_name": sci,
        "family": fields.get("Family", ""), "type_raw": fields.get("Type", ""),
        "color_raw": fields.get("Bloom Description", ""), "season_raw": fields.get("Bloom Time", ""),
        "sun_raw": fields.get("Sun", ""), "zone_raw": fields.get("Zone", ""),
        "description": desc or culture, "extra_text": culture,
    }


# ---------------- NC State Plant Toolbox ----------------
NCSU = "https://plants.ces.ncsu.edu/"


def ncsu_urls():
    xml = fetch(NCSU + "sitemap.xml")
    if not xml:
        return []
    urls = re.findall(r"<loc>(https://plants\.ces\.ncsu\.edu/plants/[^<]+)</loc>", xml)
    # species pages only (cultivar slugs usually contain a quoted name -> longer)
    urls = [u for u in urls if u.rstrip("/").count("-") <= 2]
    print(f"  {len(set(urls))} candidate pages")
    return spread(urls)


def ncsu_parse(url, html):
    s = BeautifulSoup(html, "lxml")
    dl = {}
    for dt in s.select("dt"):
        k = clean(dt.get_text(" ")).rstrip(":")
        values = []  # multi-value fields have one <dd> per value
        for el in dt.find_next_siblings():
            if el.name != "dd":
                break
            values.append(clean(el.get_text(" ")))
        if values and k not in dl:
            dl[k] = ", ".join(values)
    if "Flower Color" not in dl:
        return None  # not a flowering plant entry
    h1 = s.h1
    em = h1.find("em") if h1 else None  # the scientific name; the rest of the <small> is the audio player
    sci = clean(em.get_text(" ")) if em else clean(h1.get_text(" ")).replace("Play pronunciation", "").strip() if h1 else ""
    # alias pages (/plants/<species>/common-name/<alias>/) put the alias in front of the scientific name:
    # it is the name the page is about, unless it just repeats the scientific name
    alias = clean(" ".join(h1.find_all(string=True, recursive=False))) if h1 else ""
    first = s.select_one("#common_names li")
    common = alias if alias and alias.lower() != sci.lower() else clean(first.get_text(" ")) if first else ""
    # first full-size plant photo (thumb_sm ones are "related plants"); drop the expiring S3 signature
    # (must be an <img> with an image extension: the pronunciation audio lives under media/images/audio/,
    # and partner logos sit among the photos under media/images/partner_logos/)
    photo = (r'<img[^>]+src="(https://eit-planttoolbox-prod\.s3\.amazonaws\.com/media/images/'
             r'(?!thumb|audio|partner_logos)[^"?]+\.(?:%s))["?]')
    img = (re.search(photo % "jpe?g|png|webp", html, re.I)
           or re.search(photo % "jpe|jfif", html, re.I))  # some pages only have these JPEG variants
    return {
        "source": "NC State Plant Toolbox", "url": url,
        "image": img.group(1) if img else "",
        "name": common or sci, "scientific_name": sci,
        "family": dl.get("Family", ""), "type_raw": dl.get("Plant Type", "") + " " + dl.get("Life Cycle", ""),
        "color_raw": dl.get("Flower Color", ""), "season_raw": dl.get("Flower Bloom Time", ""),
        "sun_raw": dl.get("Light", ""), "zone_raw": dl.get("USDA Plant Hardiness Zone", ""),
        "description": dl.get("Description", ""), "extra_text": dl.get("Flower Description", ""),
    }


# ---------------- Lady Bird Johnson Wildflower Center ----------------
WF = "https://www.wildflower.org/plants/"
WF_FAMILIES = ["Asteraceae", "Lamiaceae", "Iridaceae", "Liliaceae", "Ranunculaceae", "Rosaceae",
               "Onagraceae", "Malvaceae", "Fabaceae", "Plantaginaceae", "Boraginaceae",
               "Campanulaceae", "Orchidaceae", "Polemoniaceae", "Asclepiadaceae", "Apocynaceae",
               "Verbenaceae", "Caprifoliaceae", "Papaveraceae", "Amaryllidaceae"]


def wf_urls():
    urls = []
    for fam in WF_FAMILIES:
        start = 0
        while True:  # result pages of 30 plants, in alphabetical order
            url = f"{WF}search.php?search_field=&newsearch=true&family={fam}&pagecount=30"
            html = fetch(url + (f"&start={start}" if start else ""))
            if not html:
                break
            ids = re.findall(r"result\.php\?id_plant=([A-Z0-9]+)", html)
            new = [f"{WF}result.php?id_plant={i}" for i in dict.fromkeys(ids)]
            if not set(new) - set(urls):
                break
            urls += new
            if f"start={start + 30}&" not in html:
                break
            start += 30
    print(f"  {len(set(urls))} candidate pages")
    return spread(urls)


WF_LABEL = re.compile(r"^[A-Z][A-Za-z0-9 /()'-]{1,40}:$")
WF_BINOMIAL = re.compile(r"^[A-Z][a-z]+ (?:x |× )?[a-z-]+(?: (?:var|ssp|subsp)\.? [a-z-]+)?$")


def wf_parse(url, html):
    """Line-based (no multi-line regex: those backtracked catastrophically on these pages)."""
    s = BeautifulSoup(html, "lxml")
    lines = [clean(l) for l in s.get_text("\n", strip=True).split("\n")]
    lines = [l for l in lines if l]

    def grab(label):
        try:
            i = lines.index(label + ":")
        except ValueError:
            return ""
        out = []
        for l in lines[i + 1: i + 40]:
            if WF_LABEL.match(l):
                break
            out.append(l)
        return clean(" ".join(out)).replace(" ,", ",")

    fi = next((i for i, l in enumerate(lines) if re.fullmatch(r"[A-Z][a-z]+aceae", l)
               and i + 1 < len(lines) and lines[i + 1].endswith("Family)")), None)
    if fi is None or fi < 3:
        return None
    family, common = lines[fi], lines[fi - 1]
    sci = next((lines[j] for j in range(fi - 2, max(fi - 8, -1), -1) if WF_BINOMIAL.match(lines[j])), "")
    if not sci:
        return None
    desc = ""
    if "USDA Native Status:" in lines:
        i = lines.index("USDA Native Status:")
        prose = []
        for l in lines[i + 1: i + 120]:
            if l in ("From the Image Gallery", "Plant Characteristics"):
                break
            if len(l) > 3 or prose:  # skip short native-status codes before the prose starts
                prose.append(l)
        desc = clean(" ".join(prose))
        # strip the native-status codes that precede the prose, e.g. ", AK (N) , CAN (N) , GL (N)"
        desc = re.sub(r"^(?:[\s,]*(?:[A-Z][A-Z0-9]{1,3})?\s*\([A-Z?]{1,3}\))+[\s,]*", "", desc)
        if not re.search(r"[a-z]{3}", desc):
            desc = ""
    img = re.search(r'src="\.\./(image_archive/320x240/[^"]+)"', html)
    return {
        "source": "Lady Bird Johnson Wildflower Center", "url": url,
        "image": "https://www.wildflower.org/" + img.group(1) if img else "",
        "name": common.split(",")[0], "scientific_name": sci, "family": family,
        "type_raw": grab("Habit") + " " + grab("Duration"),
        "color_raw": grab("Bloom Color"), "season_raw": grab("Bloom Time"),
        "sun_raw": grab("Light Requirement"), "zone_raw": "",
        "description": desc, "extra_text": grab("Conditions Comments"),
    }


SOURCES = {"mbg": (mbg_urls, mbg_parse), "ncsu": (ncsu_urls, ncsu_parse), "wf": (wf_urls, wf_parse)}


def main():
    global DELAY
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-source", type=int, default=500)
    ap.add_argument("--delay", type=float, default=1.0)
    ap.add_argument("--only", default="mbg,ncsu,wf")
    a = ap.parse_args()
    DELAY = a.delay
    records, seen = [], set()
    for key in a.only.split(","):
        urls_fn, parse_fn = SOURCES[key]
        n = 0
        print(f"== {key}")
        for url in urls_fn():
            if n >= a.per_source:
                break
            html = fetch(url)
            if not html:
                continue
            try:
                raw = parse_fn(url, html)
            except Exception as e:  # keep crawling on a bad page
                print("  ! parse", url, e)
                continue
            if not raw:
                continue
            rec = normalize(raw)
            if not rec or not rec["colors"] or not rec["image"]:
                continue  # keep flowering plants that have a photo
            dedup = (rec["scientific_name"].lower(), rec["source"])
            if dedup in seen:
                continue
            seen.add(dedup)
            records.append(rec)
            n += 1
            if n % 25 == 0:
                print(f"  {n} records")
        print(f"  {key}: {n} records")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for i, r in enumerate(records):
            r["id"] = i
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"wrote {len(records)} records -> {OUT}")


if __name__ == "__main__":
    main()

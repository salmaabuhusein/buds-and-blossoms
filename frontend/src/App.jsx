import { useEffect, useRef, useState } from "react";

const COLORS = ["White", "Yellow", "Orange", "Red", "Pink", "Purple", "Blue", "Green"];
const SEASONS = ["Spring", "Summer", "Autumn", "Winter"];
const SUN = ["Full sun", "Partial shade", "Full shade"];
const DOT = {
  White: "#f1ede6", Yellow: "#d8b74a", Orange: "#d9874a", Red: "#b8433a",
  Pink: "#d27ba6", Purple: "#6c4d8e", Blue: "#5b6fc4", Green: "#7c9a5f",
};
const TINT = {
  White: ["#efede8", "#8a8577"], Yellow: ["#f7eecf", "#b79a3a"], Orange: ["#f6e3d2", "#c97b45"],
  Red: ["#f4dbd7", "#a8463d"], Pink: ["#f3dfe9", "#a3537a"], Purple: ["#e7e0f0", "#5f4a86"],
  Blue: ["#dfe4f4", "#4d61a8"], Green: ["#e4ecda", "#5f7d48"],
};
const EXAMPLES = ["pink orchid", "shade woodland perennial", "fragrant climbing vine", "winter flowers"];
const EMPTY = { colors: [], seasons: [], sun: [], type: [], source: [], zone: "" };

const NO_FEEDBACK = { relevant: [], rejected: [] };
// evaluation baseline: open the page with ?feedback=off
const FEEDBACK_ON = new URLSearchParams(window.location.search).get("feedback") !== "off";

const PAGE_SIZE = 48; // fills 2, 3, 4 or 6 grid columns evenly

function buildQuery(q, f, sort, fb, page) {
  const p = new URLSearchParams();
  if (q) p.set("q", q);
  for (const k of ["colors", "seasons", "sun", "type", "source"]) f[k].forEach((v) => p.append(k, v));
  if (f.zone) p.set("zone", f.zone);
  p.set("sort", sort);
  for (const k of ["relevant", "rejected"]) fb[k].forEach((id) => p.append(k, id));
  p.set("page", page);
  p.set("page_size", PAGE_SIZE);
  return p.toString();
}

// 1 … 4 5 6 … 31: first, last and the pages around the current one; null marks a gap
function pageList(page, pages) {
  const keep = [...new Set([1, page - 1, page, page + 1, pages])].filter((n) => n >= 1 && n <= pages).sort((a, b) => a - b);
  const out = [];
  keep.forEach((n, i) => {
    const prev = keep[i - 1] || 0;
    if (n - prev === 2) out.push(prev + 1); // a gap of one page: show the page instead of "…"
    else if (n - prev > 2) out.push(null);
    out.push(n);
  });
  return out;
}

/* ---------- icons ---------- */
const Logo = () => (
  <svg width="36" height="36" viewBox="0 0 40 40" aria-hidden="true">
    {[0, 90, 180, 270].map((r) => <ellipse key={r} cx="20" cy="10.5" rx="7" ry="9.5" fill="#8e4a6e" transform={`rotate(${r + 12} 20 20)`} />)}
    <circle cx="20" cy="20" r="4.2" fill="#f6eef1" />
  </svg>
);
const Leaf = ({ color }) => (
  <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round">
    <path d="M20 4c-8 0-14 4.5-14 11 0 2 .6 3.6 1.6 5" />
    <path d="M20 4c0 9-4.5 15-11 15-1 0-2-.2-2.8-.5" />
    <path d="M4 21c3.5-5 7-8.5 12-12" />
  </svg>
);
const Chevron = () => (
  <svg className="chev" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="m5 9 7 7 7-7" /></svg>
);
const ListIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round">
    <path d="M9 6h11M9 12h11M9 18h11" /><circle cx="4.5" cy="6" r="1" /><circle cx="4.5" cy="12" r="1" /><circle cx="4.5" cy="18" r="1" />
  </svg>
);
const GridIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6">
    <rect x="4" y="4" width="6" height="6" rx="1" /><rect x="14" y="4" width="6" height="6" rx="1" />
    <rect x="4" y="14" width="6" height="6" rx="1" /><rect x="14" y="14" width="6" height="6" rx="1" />
  </svg>
);
const Check = () => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="m5 12 5 5 9-10" /></svg>);
const Cross = () => (<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M6 6l12 12M18 6 6 18" /></svg>);

/* ---------- small pieces ---------- */
function Thumb({ colors, image }) {
  const [failed, setFailed] = useState(false);
  const [bg, fg] = TINT[colors[0]] || TINT.Green;
  return (
    <div className="thumb" style={{ background: bg }}>
      {image && !failed ? (
        <img src={image} alt="" loading="lazy" referrerPolicy="no-referrer" onError={() => setFailed(true)} />
      ) : (
        <Leaf color={fg} />
      )}
    </div>
  );
}
const Dots = ({ colors }) => (
  <div className="dots">{colors.map((c) => <span key={c} className="dot" style={{ background: DOT[c] }} />)}</div>
);
const zones = (r) => (r.zone_min == null ? "—" : r.zone_min === r.zone_max ? `${r.zone_min}` : `${r.zone_min}–${r.zone_max}`);

function CheckRow({ label, count, checked, onChange, dot }) {
  return (
    <label className={"check" + (count === 0 && !checked ? " dim" : "")}>
      <input type="checkbox" checked={checked} onChange={onChange} />
      {dot && <span className="dot" style={{ background: DOT[label] }} />}
      <span className="lbl">{label}</span>
      <span className="count">{count ?? 0}</span>
    </label>
  );
}

function Sidebar({ facets, filters, setFilters }) {
  const [showAllTypes, setShowAllTypes] = useState(false);
  const toggle = (key, v) =>
    setFilters((f) => ({ ...f, [key]: f[key].includes(v) ? f[key].filter((x) => x !== v) : [...f[key], v] }));
  const f = facets || {};
  const types = Object.keys(f.type || {});
  const shownTypes = showAllTypes ? types : types.slice(0, 6);
  const sources = Object.keys(f.source || {});
  return (
    <aside className="sidebar">
      <div className="side-head">
        <h3>Filter</h3>
        <button className="link" onClick={() => setFilters(EMPTY)}>Clear all</button>
      </div>

      <section>
        <h4>Flower colour</h4>
        <div className="grid2">
          {COLORS.map((c) => (
            <CheckRow key={c} label={c} dot count={f.colors?.[c]} checked={filters.colors.includes(c)} onChange={() => toggle("colors", c)} />
          ))}
        </div>
      </section>
      <section>
        <h4>Bloom season</h4>
        {SEASONS.map((s) => (
          <CheckRow key={s} label={s} count={f.seasons?.[s]} checked={filters.seasons.includes(s)} onChange={() => toggle("seasons", s)} />
        ))}
      </section>
      <section>
        <h4>Sun exposure</h4>
        {SUN.map((s) => (
          <CheckRow key={s} label={s} count={f.sun?.[s]} checked={filters.sun.includes(s)} onChange={() => toggle("sun", s)} />
        ))}
      </section>
      <section>
        <h4>Hardiness zone (USDA)</h4>
        <div className="select">
          <select value={filters.zone} onChange={(e) => setFilters((x) => ({ ...x, zone: e.target.value }))}>
            <option value="">Any zone</option>
            {Array.from({ length: 13 }, (_, i) => i + 1).map((z) => <option key={z} value={z}>Zone {z}</option>)}
          </select>
          <Chevron />
        </div>
        <p className="hint">Plants that survive winters in your zone.</p>
      </section>
      <section>
        <h4>Plant type</h4>
        {shownTypes.map((t) => (
          <CheckRow key={t} label={t} count={f.type[t]} checked={filters.type.includes(t)} onChange={() => toggle("type", t)} />
        ))}
        {types.length > 6 && (
          <button className="link more" onClick={() => setShowAllTypes((v) => !v)}>
            {showAllTypes ? "Show less" : `Show ${types.length - 6} more`}
          </button>
        )}
      </section>
      <section>
        <h4>Source</h4>
        {sources.map((s) => (
          <CheckRow key={s} label={s} count={f.source[s]} checked={filters.source.includes(s)} onChange={() => toggle("source", s)} />
        ))}
      </section>
      <div className="vine" aria-hidden="true" />
    </aside>
  );
}

function FeedbackButtons({ record, value, mark }) {
  return (
    <div className="fb">
      <button className={value === 1 ? "on yes" : ""} title="Relevant" aria-label={`${record.name}: relevant`} aria-pressed={value === 1} onClick={() => mark(record.id, 1)}><Check /></button>
      <button className={value === -1 ? "on no" : ""} title="Not relevant" aria-label={`${record.name}: not relevant`} aria-pressed={value === -1} onClick={() => mark(record.id, -1)}><Cross /></button>
    </div>
  );
}

function Pager({ page, pageSize, total, goTo }) {
  const pages = pageSize ? Math.ceil(total / pageSize) : 0;
  if (pages <= 1) return null;
  const from = (page - 1) * pageSize + 1, to = Math.min(page * pageSize, total);
  return (
    <nav className="pager" aria-label="Result pages">
      <span className="muted">{from}–{to} of {total}</span>
      <div className="pages">
        <button disabled={page === 1} onClick={() => goTo(page - 1)} aria-label="Previous page">‹</button>
        {pageList(page, pages).map((n, i) => n === null
          ? <span key={`gap${i}`} className="gap">…</span>
          : <button key={n} className={n === page ? "on" : ""} aria-current={n === page ? "page" : undefined} onClick={() => goTo(n)}>{n}</button>)}
        <button disabled={page === pages} onClick={() => goTo(page + 1)} aria-label="Next page">›</button>
      </div>
    </nav>
  );
}

function ResultsTable({ results, offset, marks, mark }) {
  return (
    <div className="table">
      <div className="thead">
        <div>#</div><div>Plant record</div><div>Family · Type</div><div>Bloom</div>
        <div>Light</div><div>Zones</div><div>Score</div>{FEEDBACK_ON && <div className="right">Relevant?</div>}
      </div>
      {results.map((r, i) => (
        <div className="row" key={r.id}>
          <div className="num">{offset + i + 1}</div>
          <div className="plant">
            <Thumb colors={r.colors} image={r.image} />
            <div>
              <a className="pname" href={r.url} target="_blank" rel="noreferrer" dangerouslySetInnerHTML={{ __html: r.name_html }} />
              <div className="sci"><em>{r.scientific_name}</em><span> · {r.source}</span></div>
              <p className="snippet" dangerouslySetInnerHTML={{ __html: r.snippet }} />
            </div>
          </div>
          <div className="small">{r.family}<span className="muted">{r.type}</span></div>
          <div className="small"><Dots colors={r.colors} />{r.seasons.join(", ") || "—"}</div>
          <div className="small">{r.sun.join(", ") || "—"}</div>
          <div className="small">{zones(r)}</div>
          <div className="small muted">{r.score ?? "—"}</div>
          {FEEDBACK_ON && <div className="right"><FeedbackButtons record={r} value={marks[r.id]} mark={mark} /></div>}
        </div>
      ))}
    </div>
  );
}

function ResultsGrid({ results, marks, mark }) {
  return (
    <div className="cards">
      {results.map((r) => (
        <div className="card" key={r.id}>
          <a href={r.url} target="_blank" rel="noreferrer">
            <Thumb colors={r.colors} image={r.image} />
            <div className="pname" dangerouslySetInnerHTML={{ __html: r.name_html }} />
            <div className="sci"><em>{r.scientific_name}</em></div>
            <p className="snippet" dangerouslySetInnerHTML={{ __html: r.snippet }} />
            <div className="small"><Dots colors={r.colors} />{[r.seasons.join(", "), r.sun.join(", ")].filter(Boolean).join(" · ")}</div>
          </a>
          {FEEDBACK_ON && <FeedbackButtons record={r} value={marks[r.id]} mark={mark} />}
        </div>
      ))}
    </div>
  );
}

function AboutDialog({ dialogRef, stats }) {
  const close = () => dialogRef.current.close();
  return (
    <dialog className="about" ref={dialogRef} aria-labelledby="about-title" onClick={(e) => { if (e.target === e.currentTarget) close(); }}>
      <div className="about-body">
        <button className="about-close" aria-label="Close" onClick={close}><Cross /></button>
        <h2 id="about-title">Where these records come from</h2>
        {stats ? (
          <>
            <p>
              {stats.records} plant records were crawled from {stats.sources} public plant databases, normalised to one
              schema (flower colour, bloom season, sun exposure, USDA zone, plant type) and indexed with BM25.
            </p>
            <ul>
              {Object.entries(stats.by_source).map(([s, n]) => <li key={s}><span>{s}</span><span className="count">{n} records</span></li>)}
            </ul>
          </>
        ) : <p>Record counts couldn’t be loaded.</p>}
      </div>
    </dialog>
  );
}

export default function App() {
  const about = useRef(null);
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState(EMPTY);
  const [sort, setSort] = useState("name");
  const [view, setView] = useState("list");
  const [data, setData] = useState({ total: 0, page: 1, page_size: PAGE_SIZE, results: [], facets: null });
  const [stats, setStats] = useState(null);
  const [marks, setMarks] = useState({}); // ✓ = 1, ✗ = -1, not yet sent
  const [applied, setApplied] = useState(NO_FEEDBACK); // feedback behind the current ranking
  const [loading, setLoading] = useState(true); // the first search starts right away
  const [error, setError] = useState(false);
  const [retry, setRetry] = useState(0);
  const resultsTop = useRef(null);
  // the page belongs to one search: any new query, filter, sort or feedback starts again at page 1
  const searchKey = JSON.stringify([query, filters, sort, applied]);
  const [pageAt, setPageAt] = useState({ key: searchKey, page: 1 });
  const page = pageAt.key === searchKey ? pageAt.page : 1;
  const goTo = (n) => {
    setPageAt({ key: searchKey, page: n });
    resultsTop.current?.scrollIntoView({ block: "start" });
  };

  useEffect(() => { fetch("/api/stats").then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); }).then(setStats).catch(() => {}); }, []);
  useEffect(() => {
    let current = true; // ignore responses to requests that have been superseded
    setLoading(true);
    fetch("/api/search?" + buildQuery(query, filters, sort, applied, page))
      .then((r) => { if (!r.ok) throw new Error(`HTTP ${r.status}`); return r.json(); })
      .then((d) => { if (current) { setData(d); setError(false); } })
      .catch(() => { if (current) setError(true); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [query, filters, sort, applied, page, retry]);

  // with a query, default to relevance; without one, relevance means nothing, so default to A–Z
  const submit = (q) => {
    setInput(q); setQuery(q.trim()); setMarks({}); setApplied(NO_FEEDBACK);
    setSort(q.trim() ? "relevance" : "name");
  };
  const mark = (id, v) => setMarks((m) => ({ ...m, [id]: m[id] === v ? 0 : v }));
  const marked = (v) => Object.keys(marks).filter((id) => marks[id] === v).sort();
  const relevant = marked(1), rejected = marked(-1);
  const pending = relevant.join() !== applied.relevant.join() || rejected.join() !== applied.rejected.join();
  const canRank = Boolean(query) || applied.relevant.length > 0;
  const applyFeedback = () => {
    setApplied({ relevant, rejected });
    if (relevant.length) setSort("relevance");
    else if (!query && sort === "relevance") setSort("name");
    window.scrollTo({ top: 0 });
  };
  const resetFeedback = () => {
    setMarks({}); setApplied(NO_FEEDBACK);
    if (!query && sort === "relevance") setSort("name");
  };
  const first = data.facets === null; // no search has answered yet
  const subtitle = sort === "zone" ? "By hardiness zone, hardiest first"
    : sort === "name" || !canRank ? "A to Z by common name"
    : !applied.relevant.length ? `Best matches for “${query}”`
    : `${query ? `Best matches for “${query}”, adjusted` : "Ranked"} using ${applied.relevant.length} plant${applied.relevant.length > 1 ? "s" : ""} you marked`;

  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => { submit(""); setFilters(EMPTY); }}><Logo /><span>Buds &amp; <b>Blossoms</b></span></button>
      </header>

      <section className="hero">
        <h1>Find the flower <em>you’re looking for.</em></h1>
        <form className="searchbar" onSubmit={(e) => { e.preventDefault(); submit(input); }}>
      <input aria-label="Search plants" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Name, Latin name, colour, season…" />
      <button type="submit">Search</button>
    </form>
      <div className="try">
        <span>For example</span>
        {EXAMPLES.map((ex) => <button key={ex} onClick={() => submit(ex)}>{ex}</button>)}
      </div>
      </section>
      <div className="layout">
        <Sidebar facets={data.facets} filters={filters} setFilters={setFilters} />
        <main className="results" ref={resultsTop}>
          <div className="res-head">
            <div>
              <h2>{error ? "Search unavailable" : first ? "Loading plants…" : `${data.total} plants`}</h2>
              <p className="sub">{first || error ? "" : loading ? "Searching…" : subtitle}</p>
              {!error && data.expansion?.length > 0 && <p className="sub">Also looking for: {data.expansion.join(", ")}</p>}
            </div>
            <div className="controls">
              <span className="muted">Sort</span>
              <div className="select sm">
                <select value={sort} onChange={(e) => setSort(e.target.value)}>
                  <option value="relevance" disabled={!canRank}>Relevance{canRank ? "" : " (search first)"}</option>
                  <option value="name">Name (A–Z)</option>
                  <option value="zone">Hardiness zone</option>
                </select>
                <Chevron />
              </div>
              <div className="toggle">
                <button className={view === "list" ? "on" : ""} onClick={() => setView("list")} title="Table view"><ListIcon /></button>
                <button className={view === "grid" ? "on" : ""} onClick={() => setView("grid")} title="Grid view"><GridIcon /></button>
              </div>
            </div>
          </div>
          {error ? (
            <div className="empty" role="alert">
              The search service didn’t respond properly. <button className="link" onClick={() => setRetry((n) => n + 1)}>Try again</button>
            </div>
          ) : first ? null : data.total === 0 && !loading ? (
            <div className="empty">No plants match. Try removing a filter or using a broader term.</div>
          ) : (
            <>
              {view === "list" ? (
                <ResultsTable results={data.results} offset={(data.page - 1) * data.page_size} marks={marks} mark={mark} />
              ) : (
                <ResultsGrid results={data.results} marks={marks} mark={mark} />
              )}
              <Pager page={data.page} pageSize={data.page_size} total={data.total} goTo={goTo} />
            </>
          )}
        </main>
      </div>

      <footer className="footer">
        {(relevant.length > 0 || rejected.length > 0 || pending) && (
          <div className="fb-bar">
            <span role="status">{relevant.length} relevant, {rejected.length} not relevant</span>
            <button className="fb-update" disabled={!pending} onClick={applyFeedback}>Update results</button>
            <button className="link" onClick={resetFeedback}>Reset feedback</button>
          </div>
        )}
        <button className="link" aria-haspopup="dialog" onClick={() => about.current.showModal()}>About the data</button>
      </footer>
      <AboutDialog dialogRef={about} stats={stats} />
    </>
  );
}

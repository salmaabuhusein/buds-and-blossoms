import React, { useEffect, useMemo, useState } from "react";

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

function buildQuery(q, f, sort) {
  const p = new URLSearchParams();
  if (q) p.set("q", q);
  for (const k of ["colors", "seasons", "sun", "type", "source"]) f[k].forEach((v) => p.append(k, v));
  if (f.zone) p.set("zone", f.zone);
  p.set("sort", sort);
  return p.toString();
}

/* ---------- icons ---------- */
const Logo = () => (
  <svg width="40" height="40" viewBox="0 0 40 40" aria-hidden>
    {[0, 90, 180, 270].map((r) => (
      <ellipse key={r} cx="20" cy="10.5" rx="7" ry="9.5" fill="#8e4a6e" transform={`rotate(${r} 20 20)`} />
    ))}
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
const SearchIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#8a8a85" strokeWidth="1.8" strokeLinecap="round">
    <circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" />
  </svg>
);
const FilterIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
    <path d="M3 6h18M7 12h10M10 18h4" />
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
        <span className="side-title"><FilterIcon /> Refine results</span>
        <button className="link" onClick={() => setFilters(EMPTY)}>Clear all</button>
      </div>

      <section>
        <h4>Flower color</h4>
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
      <div className="tip">
        <div className="tip-title"><Leaf color="#5f7d48" /> Search tip</div>
        <p>Combine words like a colour, a season and a condition — e.g. <em>“yellow summer full sun”</em> — then narrow down with the filters.</p>
      </div>
    </aside>
  );
}

function ResultsTable({ results, feedback, setFeedback }) {
  const mark = (id, v) => setFeedback((fb) => ({ ...fb, [id]: fb[id] === v ? undefined : v }));
  return (
    <div className="table">
      <div className="thead">
        <div>#</div><div>Plant record</div><div>Family · Type</div><div>Bloom</div>
        <div>Light</div><div>Zones</div><div>Score</div><div className="right">Relevant?</div>
      </div>
      {results.map((r, i) => (
        <div className="row" key={r.id}>
          <div className="num">{i + 1}</div>
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
          <div className="right">
            <div className="fb">
              <button className={feedback[r.id] === 1 ? "on yes" : ""} title="Relevant" onClick={() => mark(r.id, 1)}><Check /></button>
              <button className={feedback[r.id] === -1 ? "on no" : ""} title="Not relevant" onClick={() => mark(r.id, -1)}><Cross /></button>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function ResultsGrid({ results }) {
  return (
    <div className="cards">
      {results.map((r) => (
        <a className="card" key={r.id} href={r.url} target="_blank" rel="noreferrer">
          <Thumb colors={r.colors} image={r.image} />
          <div className="pname" dangerouslySetInnerHTML={{ __html: r.name_html }} />
          <div className="sci"><em>{r.scientific_name}</em></div>
          <p className="snippet" dangerouslySetInnerHTML={{ __html: r.snippet }} />
          <div className="small"><Dots colors={r.colors} />{r.seasons.join(", ")} · {r.sun.join(", ")}</div>
        </a>
      ))}
    </div>
  );
}

function About({ stats, facets }) {
  return (
    <main className="about">
      <p className="eyebrow">About the data</p>
      <h2>Where these records come from</h2>
      <p>
        {stats.records} flowering-plant records were crawled from {stats.sources} public plant databases, normalised to one
        schema (flower colour, bloom season, sun exposure, USDA zone, plant type) and indexed with BM25.
      </p>
      <ul>
        {Object.entries(facets?.source || {}).map(([s, n]) => <li key={s}><strong>{s}</strong> — {n} records</li>)}
      </ul>
    </main>
  );
}

export default function App() {
  const [tab, setTab] = useState("explore");
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [filters, setFilters] = useState(EMPTY);
  const [sort, setSort] = useState("name");
  const [view, setView] = useState("list");
  const [data, setData] = useState({ total: 0, results: [], facets: null });
  const [stats, setStats] = useState({ records: 0, sources: 0 });
  const [feedback, setFeedback] = useState({});
  const [loading, setLoading] = useState(false);

  useEffect(() => { fetch("/api/stats").then((r) => r.json()).then(setStats).catch(() => {}); }, []);
  useEffect(() => {
    setLoading(true);
    fetch("/api/search?" + buildQuery(query, filters, sort))
      .then((r) => r.json())
      .then(setData)
      .catch(() => setData({ total: 0, results: [], facets: null }))
      .finally(() => setLoading(false));
  }, [query, filters, sort]);

  // with a query, default to relevance; without one, relevance means nothing, so default to A–Z
  const submit = (q) => {
    setInput(q); setQuery(q.trim()); setFeedback({}); setTab("explore");
    setSort(q.trim() ? "relevance" : "name");
  };
  const SORT_TEXT = { relevance: `Ranked by relevance to “${query}”. Mark records to refine the ranking.`,
    name: "Sorted alphabetically by common name.", zone: "Sorted by hardiness zone, coldest-tolerant first." };
  const subtitle = useMemo(
    () => (sort === "relevance" && !query ? SORT_TEXT.name : SORT_TEXT[sort]) + (query ? "" : " Search to rank by relevance."),
    [query, sort]
  );

  return (
    <>
      <header className="topbar">
        <div className="brand" onClick={() => { submit(""); setFilters(EMPTY); }}>
          <Logo />
          <div>
            <div className="wordmark">Buds <span className="amp">&amp;</span> <span className="plum">Blossoms</span></div>
            <div className="tag">Botanical search</div>
          </div>
        </div>
        <nav>
          <button className={tab === "explore" ? "active" : ""} onClick={() => setTab("explore")}>Explore plants</button>
          <button className={tab === "about" ? "active" : ""} onClick={() => setTab("about")}>About the data</button>
        </nav>
        <div className="pill">{stats.records} records · {stats.sources} sources</div>
      </header>

      {tab === "about" ? <About stats={stats} facets={data.facets} /> : (
        <>
          <section className="hero">
            <p className="eyebrow"><span className="rule" />Discover the living world</p>
            <h1>Find the flower <em>you’re looking for.</em></h1>
            <p className="lede">
              Search plant records gathered from Missouri Botanical Garden, NC State and the Lady Bird Johnson Wildflower
              Center by name, scientific name, color, season or growing conditions.
            </p>
            <form className="searchbar" onSubmit={(e) => { e.preventDefault(); submit(input); }}>
              <SearchIcon />
              <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Try “pink orchid”, “shade-loving perennial”…" />
              <button type="submit">Search</button>
            </form>
            <div className="try">
              <span>Try:</span>
              {EXAMPLES.map((ex) => <button key={ex} className="chip" onClick={() => submit(ex)}>{ex}</button>)}
            </div>
          </section>

          <div className="layout">
            <Sidebar facets={data.facets} filters={filters} setFilters={setFilters} />
            <main className="results">
              <div className="res-head">
                <div>
                  <p className="eyebrow">Browse the collection</p>
                  <h2>{data.total} plant records</h2>
                  <p className="sub">{loading ? "Searching…" : subtitle}</p>
                </div>
                <div className="controls">
                  <span className="muted">Sort by</span>
                  <div className="select sm">
                    <select value={sort} onChange={(e) => setSort(e.target.value)}>
                      <option value="relevance" disabled={!query}>Relevance{query ? "" : " (search first)"}</option>
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
              {data.total === 0 && !loading ? (
                <div className="empty">No plants match. Try removing a filter or using a broader term.</div>
              ) : view === "list" ? (
                <ResultsTable results={data.results} feedback={feedback} setFeedback={setFeedback} />
              ) : (
                <ResultsGrid results={data.results} />
              )}
            </main>
          </div>
        </>
      )}
    </>
  );
}

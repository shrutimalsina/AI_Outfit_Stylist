import { useEffect, useRef, useState } from "react";
import OutfitCanvas from "./OutfitCanvas";
import { categories, downloadLook, imageData, request, type Look, type Match, type Piece, type Result } from "./stylist";

function Decoration({ variant }: { variant: string }) {
  return <span className={`decoration decoration--${variant}`} aria-hidden="true">
    <span /><span /><span className="decoration-dot" /><span className="decoration-heart" />
  </span>;
}

function stored<T>(key: string, fallback: T): T {
  try { return JSON.parse(localStorage.getItem(key) ?? "null") ?? fallback; }
  catch { return fallback; }
}

export default function App() {
  const [menu, setMenu] = useState(false);
  const [file, setFile] = useState<File>();
  const [piece, setPiece] = useState<Piece>();
  const [category, setCategory] = useState("top");
  const [samples, setSamples] = useState<Piece[]>([]);
  const [sampleError, setSampleError] = useState(false);
  const [result, setResult] = useState<Result>();
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [reading, setReading] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [name, setName] = useState("");
  const [looks, setLooks] = useState(() => stored<Look[]>("stylist-lookbook", []));
  const [ratings, setRatings] = useState(() => stored<Record<string, number>>("stylist-ratings", {}));
  const upload = useRef<HTMLInputElement>(null);
  const output = useRef<HTMLElement>(null);
  const imageRevision = useRef(0);
  const matches = result?.recommendations ?? [];
  const ratingKey = JSON.stringify([piece?.item_id, ...matches.map(match => match.item_id)]);
  const disabled = loading || reading;

  useEffect(() => {
    const controller = new AbortController();
    request<Piece[]>("catalog/samples", { signal: controller.signal }).then(setSamples)
      .catch(() => { if (!controller.signal.aborted) setSampleError(true); });
    return () => controller.abort();
  }, []);

  function reset() {
    imageRevision.current += 1;
    setReading(false);
    setFile(undefined);
    setPiece(undefined);
    setResult(undefined);
    setError("");
    setNotice("");
    setName("");
    if (upload.current) upload.current.value = "";
  }

  async function chooseFile(next: File) {
    reset();
    if (next.size > 5 * 1024 * 1024) { setError("Choose an image up to 5 MiB."); return; }
    const revision = imageRevision.current;
    setReading(true);
    try {
      const url = await imageData(next);
      if (revision !== imageRevision.current) return;
      setFile(next);
      setPiece({ item_id: crypto.randomUUID(), category, title: null, image_url: url });
    } catch (failure) {
      if (revision === imageRevision.current) setError(String(failure));
    } finally {
      if (revision === imageRevision.current) setReading(false);
    }
  }

  function chooseSample(sample: Piece) {
    reset();
    setPiece(sample);
    setCategory(sample.category);
    document.getElementById("discover")?.scrollIntoView();
  }

  async function generate() {
    if (!piece || disabled) return;
    setLoading(true);
    setError("");
    setNotice("");
    setResult(undefined);
    try {
      if (file || piece.image_url.startsWith("data:")) {
        const form = new FormData();
        form.append("image", file ?? await (await fetch(piece.image_url)).blob(), file?.name ?? "lookbook-photo");
        form.append("category", category);
        form.append("alternatives", "8");
        setResult(await request<Result>("recommendations", { method: "POST", body: form }));
      } else {
        setResult(await request<Result>("recommendations/by-item", {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ item_id: piece.item_id, alternatives: 8 }),
        }));
      }
      requestAnimationFrame(() => output.current?.scrollIntoView({ block: "start" }));
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Please try again.");
    } finally {
      setLoading(false);
    }
  }

  function swap(categoryToSwap?: string) {
    if (!result) return;
    const alternatives = { ...result.alternatives };
    const recommendations = matches.map(match => {
      if (categoryToSwap && match.category !== categoryToSwap) return match;
      const [next, ...remaining] = alternatives[match.category] ?? [];
      if (!next) return match;
      alternatives[match.category] = remaining;
      return next;
    });
    setResult({ ...result, recommendations, alternatives });
    setNotice(categoryToSwap ? `Updated the ${categoryToSwap}.` : "A new combination is ready.");
  }

  function saveLooks(next: Look[]) {
    try {
      localStorage.setItem("stylist-lookbook", JSON.stringify(next));
      setLooks(next);
      return true;
    } catch {
      setNotice("Browser storage is full or unavailable. Download your look to keep it.");
      return false;
    }
  }

  function saveLook() {
    if (!piece) return;
    if (saveLooks([{ id: crypto.randomUUID(), name: name.trim() || "Untitled look",
      original: { ...piece, category }, matches }, ...looks])) {
      setNotice("Saved to My Lookbook.");
      setName("");
    }
  }

  function rate(value: number) {
    const next = { ...ratings, [ratingKey]: value };
    setRatings(next);
    try { localStorage.setItem("stylist-ratings", JSON.stringify(next)); setNotice(`Rated ${value} out of 5.`); }
    catch { setNotice(`Rated ${value} out of 5 for this session.`); }
  }

  return <>
    <header className="site-header" id="home">
      <a className="wordmark" href="#home"><span aria-hidden="true">✦</span> AI Outfit <em>Stylist</em> <span aria-hidden="true">✦</span></a>
      <button className="menu-toggle secondary" aria-expanded={menu} aria-controls="site-nav" onClick={() => setMenu(!menu)}>{menu ? "Close" : "Menu"}</button>
      <nav id="site-nav" className={menu ? "open" : ""} aria-label="Main navigation">
        <a href="#home" onClick={() => setMenu(false)}>Home</a>
        <a href="#discover" onClick={() => setMenu(false)}>Discover</a>
        <a href="#fashion" onClick={() => setMenu(false)}>Fashion Today</a>
        <a href="#lookbook" onClick={() => setMenu(false)}>My Lookbook</a>
        <a className="account-link" href="#account" onClick={() => setMenu(false)}>Sign Up / Log In</a>
      </nav>
    </header>
    <main>
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-copy">
        <Decoration variant="hero" />
          <span className="hero-ornament" aria-hidden="true">✦</span>
          <h1 id="hero-title">Your Style,<br /> <em>Your Story.</em></h1>
          <p>A little intelligence. A lot of style.</p>
          <a className="primary" href="#discover">Discover Your Style <span aria-hidden="true">↓</span></a>
        </div>
        <div className="hero-image" role="img" aria-label="Editorial portrait in cream tailoring">
          <span className="hero-image-diamond" aria-hidden="true">✦</span>
          <span className="hero-image-diamond" aria-hidden="true">✦</span>
        </div>
      </section>

      <section id="discover" className="studio section-wrap">
        <Decoration variant="upload" />
        <div className="studio-intro"><h2>Choose Your Piece</h2><p>Start with one item. Find the pieces that bring the look together.</p><a href="#samples">Explore catalog samples ↓</a></div>
        <form className="upload-form" onSubmit={event => { event.preventDefault(); void generate(); }}>
          <div className={`drop-zone ${dragging ? "dragging" : ""}`}
            onDragOver={event => { event.preventDefault(); if (!disabled) setDragging(true); }}
            onDragLeave={() => setDragging(false)}
            onDrop={event => { event.preventDefault(); setDragging(false); if (!disabled && event.dataTransfer.files[0]) void chooseFile(event.dataTransfer.files[0]); }}>
            {piece && <img className="upload-preview" src={piece.image_url} alt={piece.title ?? "Your clothing photo"} />}
            <label htmlFor="clothing-photo">{piece ? "Replace photo" : "Choose a clothing photo"}</label>
            <input id="clothing-photo" ref={upload} type="file" accept="image/jpeg,image/png,image/webp" disabled={disabled}
              onChange={event => { if (event.currentTarget.files?.[0]) void chooseFile(event.currentTarget.files[0]); }} />
            <small>Drag and drop a JPEG, PNG or WebP up to 5 MiB.</small>
            {piece && <button className="text-button" type="button" disabled={disabled} onClick={reset}>Remove piece</button>}
          </div>
          <label htmlFor="category">Clothing category</label>
          <select id="category" value={category} disabled={disabled || Boolean(piece && !file && !piece.image_url.startsWith("data:"))}
            onChange={event => { setCategory(event.target.value); setResult(undefined); setNotice(""); }}>
            {categories.map(value => <option key={value}>{value}</option>)}
          </select>
          <button className="primary" disabled={!piece || disabled}>{loading ? "Curating your look…" : "Find My Style"}</button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
      </section>
      {loading && <div className="loading section-wrap" role="status">
        <Decoration variant="loading" /><span aria-hidden="true">✦</span> Finding complementary pieces…</div>}
      {piece && result && <section ref={output} className="section-wrap styled-look" aria-labelledby="outfit-heading">
        <Decoration variant="outfit" />
        <h2 id="outfit-heading">Your Styled Look</h2>
        <OutfitCanvas original={piece} matches={matches} swap={swap} canSwap={key => Boolean(result.alternatives?.[key]?.length)} />
        {result.warnings.map(warning => <p key={warning}>{warning}</p>)}
        <div className="actions">
          <button className="secondary" disabled={!matches.some(match => result.alternatives?.[match.category]?.length)} onClick={() => swap()}>Try Another Combo</button>
          <button className="secondary" onClick={() => { void downloadLook(piece, matches).catch(() => setNotice("The outfit could not be downloaded. Check that all images are available.")); }}>Download My Look</button>
        </div>
        <div className="look-controls">
          <form onSubmit={event => { event.preventDefault(); saveLook(); }}>
            <label htmlFor="look-name">Look name (optional)</label>
            <input id="look-name" value={name} maxLength={80} onChange={event => setName(event.target.value)} />
            <button className="primary">Save to My Lookbook</button>
          </form>
          <fieldset><legend>Rate This Look</legend>
            {[1, 2, 3, 4, 5].map(value => <button className="star" key={value} aria-label={`Rate ${value} out of 5`}
              aria-pressed={ratings[ratingKey] === value} onClick={() => rate(value)}>{value <= (ratings[ratingKey] ?? 0) ? "★" : "☆"}</button>)}
          </fieldset>
        </div>
      </section>}
      <div className={notice ? "section-wrap notice" : "sr-only"} role="status">{notice}</div>

      <section id="samples" className="section-wrap samples"><Decoration variant="samples" />
        <h2>Need Inspiration? <em>Try a Sample.</em></h2>
        {sampleError && <p>Catalog samples are unavailable. You can still try your own photo when the stylist is connected.</p>}
        <div className="sample-grid">{samples.map(sample => <button key={sample.item_id} disabled={disabled} onClick={() => chooseSample(sample)}>
          <img src={sample.image_url} alt={sample.title ?? sample.category} loading="lazy" />
          <span>{sample.category} <span aria-hidden="true">↗</span></span>
        </button>)}</div>
      </section>

      <section id="lookbook" className="section-wrap lookbook">
        <Decoration variant="lookbook" />
        <h2>My Lookbook</h2><p>Saved looks are stored in this browser and may disappear if you clear its data.</p>
        {looks.length === 0 && <p>Your saved outfits will appear here.</p>}
        <div className="sample-grid">{looks.map(look => <article key={look.id}>
          <button className="image-button" disabled={disabled} onClick={() => {
            reset(); setPiece(look.original); setCategory(look.original.category);
            setResult({ recommendations: look.matches, warnings: [] });
            requestAnimationFrame(() => output.current?.scrollIntoView());
          }} aria-label={`Reopen ${look.name}`}><img src={look.original.image_url} alt={look.name} loading="lazy" /></button>
          <h3>{look.name}</h3><button className="text-button" onClick={() => {
            if (saveLooks(looks.filter(entry => entry.id !== look.id))) setNotice("Removed from My Lookbook.");
          }}>Remove</button>
        </article>)}</div>
      </section>

      <section id="fashion" className="section-wrap editorial"><Decoration variant="editorial" /><h2>Fashion Today</h2>
        <p className="editorial-sequence"><span>One Piece.</span><span>Endless Possibilities.</span><em>Uniquely Yours.</em></p>
        <p>For a styling exercise, start with one silhouette, then compare how different footwear or outerwear changes the outfit.</p>
        <a href="#samples">Try it with a catalog piece ↓</a>
      </section>
      <section className="section-wrap process"><Decoration variant="process" /><h2>How It Works</h2>
        <ol><li>Upload a clothing photo.</li><li>CLIP creates a visual embedding.</li><li>Cosine similarity ranks pieces in complementary categories.</li><li>Explore your recommended outfit.</li></ol>
      </section>
      <section id="account" className="section-wrap account"><Decoration variant="account" /><h2>Sign Up / Log In</h2><p>Accounts are coming soon. You can save looks in this browser today.</p><a href="#lookbook">Open My Lookbook ↑</a></section>
    </main>
    <footer>
        <Decoration variant="footer" /><a className="wordmark" href="#home"><span aria-hidden="true">✦</span> AI Outfit <em>Stylist</em> <span aria-hidden="true">✦</span></a><p>Junior Seminar · Polyvore research project</p></footer>
  </>;
}

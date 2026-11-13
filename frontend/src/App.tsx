import { useEffect, useState } from "react";

type Recommendation = {
  item_id: string;
  category: string;
  title: string | null;
  similarity: number;
  image_url: string;
};
type Result = { recommendations: Recommendation[]; warnings: string[] };
const categories = ["top", "bottom", "dress", "outerwear", "footwear", "accessory"];

export default function App() {
  const [file, setFile] = useState<File>();
  const [category, setCategory] = useState("top");
  const [preview, setPreview] = useState("");
  const [result, setResult] = useState<Result>();
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!file) {
      setPreview("");
      return;
    }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  async function generate() {
    if (!file) return;
    setLoading(true);
    setError("");
    setResult(undefined);
    const form = new FormData();
    form.append("image", file);
    form.append("category", category);
    try {
      const response = await fetch("/api/v1/recommendations", { method: "POST", body: form });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message ?? "Recommendation request failed");
      setResult(data);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Recommendation request failed");
    } finally {
      setLoading(false);
    }
  }

  return <main>
    <header><h1>AI Outfit Stylist</h1><p>Discover clothing combinations powered by AI.</p></header>
    <div className="layout">
      <form onSubmit={event => { event.preventDefault(); void generate(); }}>
        <label htmlFor="image">Clothing photo</label>
        <input id="image" type="file" accept="image/jpeg,image/png,image/webp" disabled={loading}
          onChange={event => {
            const selected = event.target.files?.[0];
            setResult(undefined);
            if (selected && selected.size > 5 * 1024 * 1024) {
              setFile(undefined);
              setError("Choose an image up to 5 MiB.");
            } else {
              setFile(selected);
              setError("");
            }
          }} />
        {preview && <img className="preview" src={preview} alt="Uploaded clothing preview" />}
        <label htmlFor="category">Clothing category</label>
        <select id="category" value={category} disabled={loading}
          onChange={event => { setCategory(event.target.value); setResult(undefined); setError(""); }}>
          {categories.map(item => <option key={item}>{item}</option>)}
        </select>
        <button disabled={loading || !file}>{loading ? "Generating…" : error && file ? "Retry" : "Generate Outfit"}</button>
      </form>
      <section aria-live="polite" aria-busy={loading}>
        <h2>Outfit recommendations</h2>
        {error && <p role="alert">{error}</p>}
        {!error && !result && <p>{loading ? "Finding complementary items…" : "Upload a clothing photo to get started."}</p>}
        {result && <>
          <div className="cards">{result.recommendations.map(item => <article key={item.item_id}>
            <img src={item.image_url} alt={item.title ?? item.category} />
            <h3>{item.title ?? item.category}</h3>
            <p>{item.category} · cosine similarity {item.similarity.toFixed(3)}</p>
          </article>)}</div>
          {result.warnings.map(warning => <p key={warning}>{warning}</p>)}
        </>}
      </section>
    </div>
  </main>;
}

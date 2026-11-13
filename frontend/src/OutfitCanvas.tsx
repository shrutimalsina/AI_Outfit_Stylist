import { useRef, useState } from "react";
import { type Match, type Piece } from "./stylist";

export default function OutfitCanvas({ original, matches, swap, canSwap }: {
  original: Piece; matches: Match[]; swap: (category: string) => void;
  canSwap: (category: string) => boolean;
}) {
  const [view, setView] = useState<"grid" | "before">("grid");
  const [preview, setPreview] = useState<Piece>();
  const dialog = useRef<HTMLDialogElement>(null);

  function enlarge(piece: Piece) {
    setPreview(piece);
    dialog.current?.showModal();
  }

  return <>
    <div className="view-switch" aria-label="Outfit view">
      {(["grid", "before"] as const).map(mode =>
        <button key={mode} type="button" aria-pressed={view === mode} onClick={() => setView(mode)}>
          {mode === "before" ? "Before" : "After · Grid"}
        </button>)}
    </div>
    <div className={`outfit-board ${view}`}>
      <article className="original-card">
        <button className="image-button" type="button" onClick={() => enlarge(original)} aria-label="Enlarge your original piece">
          <img src={original.image_url} alt={original.title ?? "Your original piece"} />
        </button>
        <div className="piece-copy"><span className="eyebrow">The starting piece</span><h3>{original.title ?? "Your original piece"}</h3></div>
      </article>
      {view !== "before" && matches.map(match =>
        <article className="match-card" key={match.item_id}>
          <div className="image-wrap">
            <button className="image-button" type="button" onClick={() => enlarge(match)} aria-label={`Enlarge ${match.title ?? match.category}`}>
              <img src={match.image_url} alt={match.title ?? match.category} />
            </button>
          </div>
          <div className="piece-copy">
            <span className="eyebrow">{match.category}</span>
            <h3>{match.title ?? match.category}</h3>
            <details className="stylist-details">
              <summary>Why This Piece?</summary>
              <div className="stylist-note">
                <h4>A Note From Your Stylist</h4>
                <p>CLIP ranked this piece within the complementary {match.category} category by visual similarity.</p>
                <p className="stylist-score"><em>Cosine similarity</em> {match.similarity.toFixed(3)}</p>
              </div>
            </details>
            <button className="text-button" disabled={!canSwap(match.category)} onClick={() => swap(match.category)}>Swap This Piece ↻</button>
          </div>
        </article>)}
    </div>
    <dialog ref={dialog} aria-label="Clothing preview">
      <form method="dialog"><button className="secondary" autoFocus>Close</button></form>
      {preview && <><img src={preview.image_url} alt={preview.title ?? preview.category} /><h3>{preview.title ?? preview.category}</h3></>}
    </dialog>
  </>;
}

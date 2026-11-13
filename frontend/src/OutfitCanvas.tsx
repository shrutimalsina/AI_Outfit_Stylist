import { useRef, useState } from "react";
import { type Match, type Piece } from "./stylist";

export default function OutfitCanvas({ original, matches, swap, canSwap }: {
  original: Piece; matches: Match[]; swap: (category: string) => void;
  canSwap: (category: string) => boolean;
}) {
  const [view, setView] = useState<"collage" | "grid" | "before">("collage");
  const [preview, setPreview] = useState<Piece>();
  const dialog = useRef<HTMLDialogElement>(null);

  function enlarge(piece: Piece) {
    setPreview(piece);
    dialog.current?.showModal();
  }

  return <>
    <div className="view-switch" aria-label="Outfit view">
      {(["collage", "grid", "before"] as const).map(mode =>
        <button key={mode} type="button" aria-pressed={view === mode} onClick={() => setView(mode)}>
          {mode === "before" ? "Before" : mode === "collage" ? "After · Collage" : "Grid"}
        </button>)}
    </div>
    <div className={`outfit-board ${view}`} key={view}>
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
            <div className="explanation hover-explanation" aria-hidden="true">
              <strong>Why This Piece?</strong><p>Ranked within the complementary {match.category} category by CLIP visual similarity.</p>
              <span>Cosine similarity · {match.similarity.toFixed(3)}</span>
            </div>
          </div>
          <div className="piece-copy">
            <span className="eyebrow">{match.category}</span>
            <h3>{match.title ?? match.category}</h3>
            <details><summary>Why This Piece?</summary><p>Ranked within the complementary {match.category} category by CLIP visual similarity. Score: {match.similarity.toFixed(3)}.</p></details>
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

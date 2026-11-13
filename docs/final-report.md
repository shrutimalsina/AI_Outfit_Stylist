# AI Outfit Stylist research report

## Abstract and research objective

This project tests whether a pretrained CLIP vision encoder plus category-aware cosine retrieval can recover hidden clothing items from curated Polyvore outfits more often than a category-matched random baseline. The local original Polyvore and Re-PolyVore join supported a real held-out evaluation. CLIP recovered seven of 3,104 eligible test targets.

## Dataset and architecture

The experiment joins original Polyvore split metadata to local Re-PolyVore images by set ID and item index. Of 142,480 metadata items, 76,543 matched decodable JPEGs. The seed-42 sample retained 3,000 training, 500 validation and 500 test outfits with at least two verified images each. Only 310 sampled outfits were complete. The catalog contains 15,671 items across the original outfit-disjoint splits. The offline pipeline stores normalized NumPy embeddings and maps their rows to source items. PostgreSQL tracks snapshots and their item membership. FastAPI and the notebooks share the retrieval engine, and React calls the API.

## Methods

CLIP ViT-B/32 converts RGB images to 512-dimensional float32 embeddings. L2 normalization makes the dot product equal cosine similarity. Each clothing category defines three ordered recommendation slots. The engine picks the highest-scoring available item per slot and breaks ties by item ID. The random baseline samples from those same slots and excludes the same query item.

The [evaluation protocol](evaluation-protocol.md) describes the held-out design, transductive candidate catalog, metrics and exclusions. Use validation during development and reserve test results for final reporting.

## Results and error analysis

| Split | Eligible | CLIP Recall@3 | CLIP MRR@3 | Random mean Recall@3 |
| --- | ---: | ---: | ---: | ---: |
| Validation | 2,908 | 0.6534% | 0.004241 | 0.0502% |
| Test | 3,104 | 0.2255% | 0.001557 | 0.0480% |

The test baseline population standard deviation was 0.0401 percentage points
over 100 seeds. The test gap was 0.1775 percentage points. Absolute recovery
was low, and validation recall exceeded test recall. Missing images may bias
the retained subset, and outfit-level splits can still share products under
different outfit-scoped identifiers. These results measure exact-item
recovery in a transductive catalog.

## Limitations and future work

Fashion compatibility is subjective and multiple outfits can be valid. Exact-item recovery is a limited measure of outfit quality. Cosine similarity describes visual features, and the system does not predict physical fit or estimate changes in e-commerce returns. Future work could evaluate human judgments, multiple visible outfit items, and learned compatibility scores.

## Conclusion

CLIP recovered more held-out targets than the mean random baseline in this joined subset. The low absolute recovery and incomplete image coverage limit what the result says about general outfit quality.

## Fixture performance

On an Apple M3, a live HTTP smoke test through Vite and Uvicorn used cached CLIP weights and four synthetic catalog items. The first upload took 3.148 seconds. Across ten subsequent uploads the p95 was 0.056 seconds. A full-catalog performance run remains outstanding.

A repeatable benchmark using ten warmed samples on the same Apple M3 and
four-item fixture measured 38.4 ms p95 for CPU inference, 0.048 ms p95
for ranking, and 41.7 ms p95 for direct HTTP upload. Batch-eight inference
processed 55.6 images per second at the median. The embedding matrix occupied
8,192 bytes, excluding model weights and runtime overhead.

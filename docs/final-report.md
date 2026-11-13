# AI Outfit Stylist research report

## Abstract and research objective

This project tests whether a pretrained CLIP vision encoder plus category-aware cosine retrieval can recover hidden clothing items from curated Polyvore outfits more often than a category-matched random baseline. Real experimental results are currently unavailable because the pinned dataset file requests returned HTTP 401.

## Dataset and architecture

The planned dataset is the authors' Polyvore Outfits release, revision `22cc0c748c293a598e1df561a76abe96273cb76a`. The sampling design targets 4,000 outfits across the official item-disjoint splits. Ingestion keeps complete outfits and records missing metadata and invalid images. The offline pipeline stores normalized NumPy embeddings and maps their rows to source items. PostgreSQL tracks snapshots and their item membership. FastAPI and the notebooks share the retrieval engine, and React calls the API.

## Methods

CLIP ViT-B/32 converts RGB images to 512-dimensional float32 embeddings. L2 normalization makes the dot product equal cosine similarity. Each clothing category defines three ordered recommendation slots. The engine picks the highest-scoring available item per slot and breaks ties by item ID. The random baseline samples from those same slots and excludes the same query item.

The [evaluation protocol](evaluation-protocol.md) describes the held-out design, transductive candidate catalog, metrics and exclusions. Use validation during development and reserve test results for final reporting.

## Results and error analysis

| Measure | Polyvore test result |
| --- | --- |
| CLIP Recall@1, Recall@3 and MRR@3 | Unavailable |
| Random Recall@3 mean and standard deviation | Unavailable |
| Difference in Recall@3 | Unavailable |

All four notebooks executed with synthetic demonstration data. CPU CLIP inference was verified separately. Fixture results validate the software workflow and provide no evidence for the research hypothesis. Once the dataset is accessible, inspect misses by target category, slot position, and catalog size.

## Limitations and future work

Fashion compatibility is subjective and multiple outfits can be valid. Exact-item recovery is a limited measure of outfit quality. Cosine similarity describes visual features, and the system does not predict physical fit or estimate changes in e-commerce returns. Future work could evaluate human judgments, multiple visible outfit items, and learned compatibility scores.

## Conclusion

The evaluation workflow can run on verified inputs. A real Polyvore run is required before drawing conclusions about CLIP versus random retrieval.

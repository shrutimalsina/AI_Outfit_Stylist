# API contract

FastAPI publishes the interactive contract at `/docs` and its machine-readable
schema at `/openapi.json`.

| Method | Route | Purpose |
| --- | --- | --- |
| GET | `/health/live` | Process liveness |
| GET | `/health/ready` | Active catalog, PostgreSQL and model readiness |
| GET | `/api/v1/catalog` | Snapshot metadata |
| GET | `/api/v1/categories` | Ordered category policy |
| GET | `/api/v1/items/{item_id}` | Item metadata |
| GET | `/api/v1/items/{item_id}/image` | Catalog image |
| POST | `/api/v1/recommendations` | Multipart image, category and optional top_k |
| POST | `/api/v1/recommendations/by-item` | JSON item_id and optional top_k |
| GET | `/api/v1/evaluations/{run_id}` | Stored evaluation by UUID |

`top_k` accepts 1–3. Recommendations include category, position, cosine
similarity and image URL. Error responses contain an `error` object with
`code` and `message`. The local database-free demo supports catalog browsing
and recommendations. Readiness requires a registered PostgreSQL catalog.

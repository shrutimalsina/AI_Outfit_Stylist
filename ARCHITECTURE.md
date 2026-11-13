# Architecture

Offline Python jobs ingest official Polyvore splits, validate local images and sample complete outfits. A pinned CLIP encoder writes an immutable normalized float32 matrix and ordered row manifest. PostgreSQL 17 holds structured metadata and the active snapshot pointer. A shared Python engine will serve FastAPI, notebooks and offline evaluation. React consumes the API. Local files hold images and matrices.

The experiment uses a transductive catalog so hidden test items can be retrieved. CLIP and random retrieval use the same ordered slots and candidates. Test results are reserved for final reporting.

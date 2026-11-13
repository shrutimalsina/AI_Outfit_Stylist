# Project journal

## 2026-11-12

- Objective: test whether category-aware CLIP retrieval recovers held-out Polyvore outfit items more often than category-matched random retrieval.
- Phase 1: In progress. Desktop inspection found no existing project or Polyvore filenames. Python 3.11 and Node are available; uv and Docker were not found on PATH.
- Next: verify the upstream schema and implement deterministic ingestion.
- Dataset and model artifacts: Not started. Research results: unavailable.

- Phase 1 checkpoint: Completed and verified for ingestion dependencies. Python 3.11.16 created .venv; Pillow 11.3.0 and NumPy 2.2.6 installed after retrying outside the sandbox because PyPI DNS failed inside it. Exact installed application packages are recorded in backend/requirements-checkpoint.txt. Full stack locking and uv remain pending.
- Phase 2: In progress. Authors' dataset card advertises CC BY 4.0 and reports a 4.3 GB repository. Upstream loader confirms set_id, items[].item_id, semantic_category and images/<id>.jpg. No local release was found.

- Phase 2 fixture checkpoint: Completed and verified. Added pipeline/prepare_dataset.py and four synthetic unit tests covering complete outfits, shared-item deduplication, corrupt/missing inputs, sample limits, split leakage, and deterministic manifests. The real-data phase remains unverified. The full release was not downloaded during this checkpoint.
- Verification: `.venv/bin/python -m unittest discover -s backend/tests/unit -v` ran 4 tests, all passed. CLI help ran and `.venv/bin/pip check` found no broken requirements.
- Decisions: item-disjoint official split; seed 42; 3,000/500/500 per split; whole-outfit exclusion for invalid inputs; retain unknown category metadata for auditing. Unittest is used at this checkpoint; pytest and coverage remain pending.
- Model planned: openai/clip-vit-base-patch32 revision 3d74acf9a28c67741b2f4f2ea7635f0aaf6f0268, dimension 512. No model execution or research metrics.
- Handoff: obtain the pinned authors' release and execute the README ingestion command. Verify actual category values and report sample shortfalls and exclusions. Then implement resumable CLIP extraction and validated catalog artifacts before ranking and evaluation. The four notebooks, PostgreSQL, API, React, Docker, and final research report remain not started.

## 2026-11-12 — resumed development

- Phase 2 in progress. Resuming from c185674 and checking the authors’ release layout.

- Phase 2 real-data run: Blocked. Hugging Face API reported revision 22cc0c748c293a598e1df561a76abe96273cb76a, but anonymous file downloads returned HTTP 401. This release lists image-bearing Parquet files; the existing ingestion CLI expects extracted images. PyArrow 19.0.1 installed locally for investigation and is not needed by this checkpoint. Four existing tests passed.
- Phase 3: In progress independently using synthetic fixture images and a deterministic test encoder.

- Phase 3 checkpoint: Completed and verified on synthetic inputs. Added backend/app/ml/encoder.py and pipeline/extract_embeddings.py. The official revision has no safetensors artifact, so the loader uses PyTorch 2.8.0 with weights-only loading on the pinned official file. CPU inference on a generated RGB image produced shape (1, 512), dtype float32, and norm 1.0. Six unit tests passed, including simulated interruption, row alignment and published-snapshot reuse. pip check reported no broken requirements. The ML checkpoint lock is a macOS environment freeze; a full cross-platform lock remains pending.
- Next: resolve dataset file access and inspect the pinned Parquet schema, or obtain the authors' unpacked release. In parallel with that data dependency, the next implementation phase is a checksum-validating catalog reader and deterministic category-slot ranking. No real research metrics are available.

### Phase 4 — catalog loading and ranking

- In progress. Reverified the previous checkpoint with six passing tests.

- Completed and verified. Added config/categories.yaml, the shared catalog reader and ranking engine, and five tests. Catalog loading checks both checksums, model revision, shape, dtype, row IDs and vector norms. Ranking uses policy order and lexicographic string IDs for ties, skips empty slots, and shares candidate selection with seeded random retrieval.
- Verification: all 11 unit tests passed and git diff --check passed. Tests used synthetic artifacts. Real-data access remains blocked by the recorded HTTP 401.
- Next: implement hidden-item case enumeration, Recall@1/3 and MRR@3, and comparison across 100 baseline seeds. Record exclusions and catalog/policy provenance in the evaluation report.

### Phase 5 — hidden-item evaluation

- In progress. Reverified the ranking checkpoint with 11 passing tests.

- Completed and verified on fixtures. The evaluation enumerates ordered query/hidden pairs, checks split and eligibility, compares cosine retrieval to 100 seeded random runs, and records per-case outcomes, exclusions, category metrics and artifact provenance.
- Verification: 13 unit tests passed, including known metrics and repeatable baseline results. CLI help and git diff --check passed. No real Polyvore metrics because the previously recorded dataset access blocker remains.
- Next: create the academic notebooks using the shared modules, obtain the pinned dataset, then implement and verify the API and PostgreSQL integration.

### Academic notebooks and application integration

- In progress. Building notebooks with an explicitly labeled synthetic workflow and the same modules used for real experiments.

- All four notebooks executed successfully with nbconvert and cached CLIP weights. Notebook outputs were generated outside the repository. Synthetic catalog outputs remain demonstration data.
- FastAPI routes, initial Alembic schema, and React interface are implemented. Integration checks are in progress.

- Verification: 17 pytest tests passed with 75% Python statement coverage across the measured app and pipeline modules. Ruff passed after removing an unused import. Alembic generated PostgreSQL upgrade SQL; live migrations and publication were not exercised locally because PostgreSQL and Docker executables are absent. React TypeScript and Vite build passed. API integration used TestClient and a synthetic catalog; browser-to-live-API and Compose startup remain unverified.
- Added PostgreSQL snapshot publication, React upload and result display, Dockerfiles/Compose, CI, README commands and research report. Evaluation report lookup currently reads UUID-named local JSON reports; PostgreSQL evaluation/request tables are migrated but application writes are pending. Runtime lock was captured on macOS and container installation remains unverified.
- Next: verify CI PostgreSQL integration, run Compose and browser smoke tests, obtain authorized Polyvore files, and run validation then the frozen test evaluation. Real research metrics and warmed API performance remain unavailable.

- Live HTTP smoke check passed through Vite to Uvicorn with cached CPU CLIP, returning three fixture recommendations for each of 11 uploads. Apple M3, one cold request 3.148 s, ten warmed requests p95 0.056 s. This does not establish performance with a full Polyvore catalog. GitHub CLI is unauthenticated, so remote Actions status was not verified.

### PostgreSQL persistence

- In progress. Adding transactional evaluation registration and request metadata logging.

- Completed and verified against PostgreSQL 17.11 on an isolated loopback cluster. Alembic upgraded, downgraded, and upgraded again. The integration test verified repeat publication, embedding row mappings, evaluation report and case persistence, readiness, and recommendation-request logging. All 18 tests and Ruff passed. CI now runs the same database test against its PostgreSQL service.
- Evaluation exclusions with unresolved foreign keys remain in the stored report JSON. The API still supports local reports when no database record is available. Recommendation logging stores IDs and categories without image payloads.
- Next: verify Compose in a Docker-capable environment and resolve Polyvore access for the real evaluation. Fixture timing remains the only latency measurement.

# Project completion checklist

| Deliverable | Verification |
| --- | --- |
| Data preparation and official split preservation | Joined original metadata with local Re-PolyVore images; sampled 4,000 outfits |
| CLIP embeddings and retrieval | Validated 15,671 image hashes and cached vectors; verified category slots in API and browser |
| Hidden-item evaluation | Validation and test runs with Recall@3, MRR@3 and 100 baseline seeds |
| PostgreSQL, migrations and API | Published the real catalog and retrieved its stored evaluation from a migrated PostgreSQL 17 instance |
| React and Docker Compose | Real upload and result images verified in Chromium; production overlay passed Linux CI with a fixture |
| Notebooks and research report | All four notebooks executed on real data; report includes results, performance and limitations |
| Reproducibility | Python and npm locks, asset validation CLI, README commands and project journal |
| Public hosting | Deferred at the user's request; deployment runbook is available |

Split preservation is part of ingestion because the source supplies official
splits. The pipeline does not generate replacement splits. See the
[dataset decision](decisions/001-local-polyvore-join.md) and
[final report](final-report.md) for the limits of the joined sample.

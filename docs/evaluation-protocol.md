# Hidden-item evaluation

Use the official validation split for development and freeze the policy before reporting on the test split. Each ordered pair of distinct items from a sampled outfit supplies one query and one hidden target. The query is the only ranking input. Excluded cases are recorded individually, and ingestion exclusions appear separately. Outfits with more items contribute more cases.

This is transductive retrieval. The catalog includes the held-out items, so the experiment measures whether the system retrieves them from the same candidate universe. Both methods use the same category slots, catalog and query exclusion. For each seed from 0 through 99, the baseline draws uniformly from the candidates in each slot.

Recall@1 is the fraction of eligible cases recovered at rank one. Recall@3 is the fraction recovered among the first three recommendations. MRR@3 averages the reciprocal position, with zero contribution for a miss. Baseline standard deviation is the population standard deviation across the 100 seeded runs.

Exact-item recovery can miss other valid combinations, and visual similarity can disagree with human judgments of compatibility. Position also depends on the category policy because the system emits one result per slot.

## Local original Polyvore and Re-PolyVore join

The local dataset uses original outfit splits and image keys formed from outfit
ID and item index. Each sampled group has at least two verified JPEGs. Many
groups are partial because the image archive covers only part of the original
metadata. Report results for the joined subset and retain the compatibility audit.
The same product can occur under multiple outfit-scoped IDs. Candidate images
from all three splits are available at ranking time.

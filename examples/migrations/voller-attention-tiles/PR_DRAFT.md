# Draft — Attention Tiles source adapter and portable evidence records

**Do not submit this as a completed bounty claim yet.** The actual service migration, retrieval results, live video and public showcase are pending.

When an invention catalogue moves between memory systems, a summary alone can lose its original source pointers and evidence limitations. This example adapts a real Voller Attention Tiles snapshot to OKF while preserving complete source records, parent references, dates and unknown fields.

The adapter feeds Memanto's existing OKF migration command. It adds reverse reconstruction and integrity checks, and includes a reproducible public-source sample. It refuses oversize records instead of silently truncating source data.

Executed locally: official CLI preview, native mapper/export-format round trip, 11 new adapter tests, and 20 upstream OKF/migration tests. The complete upstream suite also passed with 970 passing tests and 24 live-service skips; all pre-commit hooks passed. All 77 tiles in the private source snapshot were restored exactly; the included public-source sample contains 66. These are local format tests, not a completed backend migration or semantic recall result.

Contributor onboarding for `jaonnvoller-ai` was completed in merged PR #1981. Before submission, attach the actual service run report, live recording and public showcase links, and link the BountyHub claim. Related challenge: #1609. No closing keyword is included because other submissions compete on the same issue.

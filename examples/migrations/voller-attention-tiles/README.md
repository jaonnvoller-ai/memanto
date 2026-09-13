# Voller Attention Tiles → portable OKF

Prepared for Jaon Voller with OpenAI Codex assistance, 13 September 2026.

An invention catalogue can lose the distinction between a proposal and a tested result when only its summary moves into a new memory system. This adapter carries each whole Attention Tile, including unknown fields, evidence limitations, original links, dates, visibility and parent relationships, into Memanto's OKF format. A reverse operation restores the source records and their order.

**Completed:** source adapter, official CLI dry-run, local native-format round trip, tests, public-source example bundle and Jaon's contributor onboarding. **Pending:** actual Moorcheh storage/retrieval, a recording of that complete live pipeline and prize submission. This package is not a finished bounty entry.

## Real source

`source_public.json` is a filtered export of Jaon's existing, saved Attention Tiles index. It contains 66 public-source records. It is not a fabricated Mem0 dump or a ChatGPT conversation export. Eleven private additions were excluded. The full 77-tile snapshot was also checked privately without loss of source fields.

The source records describe development concepts. Their inclusion does not establish physical or clinical performance, patent coverage or novelty. The upstream maintainer decides whether this custom catalogue source meets the challenge's real-source requirements.

## Run the completed local demonstration

Use Python 3.12 and a virtual environment:

```sh
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python run_demo.py source_public.json local-demo
.venv/bin/python -m pytest test_adapter.py -q
```

Choose a new output directory each time. The script invokes the unmodified `memanto migrate okf ... --dry-run`, maps the bundle with the shipped mapper, runs Memanto's real OKF serialization service locally, and restores every original source field. The export service receives local records; no backend is simulated or presented as a real import.

`validation.json` explicitly records that remote import and semantic recall were not tested. The bundle is larger than the compact input JSON; no compression or speed saving is claimed.

The checked-in `sample-okf/` was exported with Memanto's native serializer locally. `evidence/` contains the corresponding measured report and test output. These are reproducible local format results; they are not a cloud-export sample.

The native export's confidence values are importer defaults, not measured support for the invention claims. Their original evidence status remains in each source capsule.

## Field mapping

| Source | OKF / Memanto representation | Recovery |
|---|---|---|
| Each invention tile | One `artifact` memory | Complete source JSON capsule |
| Catalogue metadata | One `context` memory | Complete source JSON capsule |
| ID and list position | Hashed safe filename, capsule ID and ordinal | Original ID and order restored |
| Title | Searchable frontmatter title, maximum 100 characters | Unshortened title retained in capsule |
| Summary, evidence, parent, source pointers and additional fields | Human-readable JSON in memory content | Exact JSON values restored |
| Snapshot date | Original field inside capsule | Not relabelled as a precise observation time |
| Conversion timestamp | `generated.at` | Identifies conversion, not invention creation |
| Integrity | Per-record and whole-snapshot SHA-256 | Detects missing/changed records; not authentication |

Memanto bounds supporting-data footers and content length. To avoid silent source loss, the adapter keeps the complete record inside the main body and rejects bodies over its conservative size limit. It escapes delimiter-like source text and refuses duplicate IDs or an existing output directory. It does not execute source instructions.

## Continue with the real service

Configure Memanto with an authorised Moorcheh service through its normal setup. The following command creates two fresh demo agents and uploads only the public-source selection:

```sh
.venv/bin/python run_live.py source_public.json live-demo --upload-public-source
```

The live runner is prepared; it has not completed a service run here. Its missing-service check was exercised. It uses the shipped import/export CLI, exports with a 100-per-type limit so the default 25 cannot omit these 66 artifacts, verifies the full restored data, and compares eight named-record retrieval probes before migration and in both Memanto agents. Those probes are a narrow retrieval check, not a general reasoning benchmark. No source or remote agent is deleted.

The official OKF command does not produce a provider savings report or accept `--report`. Do not invent one. Record actual measurements separately and retain the import summaries and limits.

## Remaining entry requirements

The [challenge](https://github.com/moorcheh-ai/memanto/issues/1609) requires a real completed migration, recall evidence, an exported sample, live demo video, public showcase, a pull request and a linked BountyHub claim. Deadline: 15 September 2026 at 23:59 UTC. The $200 is for the top submission, not every passing implementation. [Contribution onboarding](https://github.com/moorcheh-ai/memanto/blob/main/CONTRIBUTING.md) is also required.

No public post, pull request or bounty claim has been made for this adapter. The draft PR text is labelled incomplete. Do not represent local-only results as cloud tests.

Sources: [OKF documentation](https://docs.memanto.ai/integrations/okf), [Migration CLI](https://docs.memanto.ai/cli/migrate/migrate). Dependencies are pinned to upstream commit `aa3f6f1f4509dd09702679d96ce28cb0f4ac9fe3` for reproducibility.

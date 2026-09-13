# Voller test setup

This repository has a reusable workflow for the reviewed Attention Tiles entry. A new manual run includes the local checks and the real Moorcheh migration. There is no mode selector.

## Approved one-off cleanup

The Community account reached its five-namespace limit in run 34787075127, before the first agent could be created. Jaon explicitly approved removing the two older backed-up test namespaces on 13 September 2026:

- `memanto_agent_voller-portable-054a48145260-a`
- `memanto_agent_voller-portable-054a48145260-b`

A fresh manual run now performs this exact cleanup before the live migration. It compares all 67 memory IDs and every native OKF memory document against hashes from the verified archive of run 34781697137, reconstructs all 66 original public tiles, saves fresh raw snapshots, and uploads that backup successfully before any deletion. It then rechecks both namespaces, removes only the approved pair, and checks for two free slots. Unexpected records, changed data, incomplete pages, failed backups or delayed quota release stop the live test.

The nine cleanup safety tests use local fixtures and no service credential. Together with the existing focused tests, 49 checks passed before publication; Ruff and mypy also passed. No cloud deletion was performed during these tests. Current cloud contents and freed capacity are verified only when the new manual workflow executes.

This permission applies only to those two exact old test namespaces. The original saved archive and the public OKF sample remain available. Namespace removal is permanent in Moorcheh; the original archive retains the earlier exported data, while the fresh backup artifact retains the raw records observed immediately before deletion. Both backup and cleanup-result artifacts are retained for 30 days. Stop other writes to these disposable agents while cleanup runs; Moorcheh does not provide an atomic compare-and-delete operation here.

If the pair is already absent, cleanup makes no deletion request. It still requires two free slots before starting another two-agent test. It never deletes newer demo agents automatically or buys more capacity.

## Start the full test

Open [Voller portable memory tests](https://github.com/jaonnvoller-ai/memanto/actions/workflows/voller-tests.yml), refresh the page, choose **Run workflow**, leave branch **main** selected and press the green **Run workflow** button.

Start a new run from the workflow page. Re-running an older run uses its original workflow and source pin. To use the current readiness check, start a fresh run.

## If the run reports a missing key

1. On your signed-in phone, open [Moorcheh API keys](https://console.moorcheh.ai/api-keys) and create a dedicated key for the Voller test runner.
2. Open [this repository's Actions secrets](https://github.com/jaonnvoller-ai/memanto/settings/secrets/actions), choose **New repository secret**, enter the name **MOORCHEH_API_KEY**, paste the key in the secret field and save it. Do not put the key into chat or a source file.
3. Start a new run using the instructions above. If the secret already exists, do not replace it unless it is invalid, expired or needs rotation.

The assistant's connected GitHub tools cannot create repository secrets or start a manual workflow. Those controls remain in your GitHub interface. After a run starts, the assistant can inspect its status and evidence through the GitHub connection.

## What runs

- The local job runs the 11 adapter tests, 9 live-runner regression tests and 20 upstream format tests, then the native local format round trip. It needs no Moorcheh key.
- On a new manual run, the live job follows successful local checks. It imports the 66 public-source records into two new demo agents, exports them and checks exact reconstruction plus eight named-record retrieval probes. Before scoring, it requires two successive complete native exports to reconstruct the full source. This bounded readiness check does not use the scored questions. It then asks each of the eight questions exactly once on each agent; any scored miss still fails. Readiness observations and returned IDs appear directly in the GitHub log. The earlier diagnostic mode remains available as --diagnose-immediate in the runner; its early misses still fail.
- Push-triggered runs perform local checks only. There is no scheduled or automatic live-service run.
- Each live run uses Moorcheh service credits and creates fresh demo agents. No old agent or source data is deleted.
- Later runs reuse the saved key. Replace it only if it expires, is revoked or needs rotation; this does not guarantee permanent account access.
- The reviewed entry remains pinned to commit `9a821ca9b08673b570a63de7c23524600516a3e5`. Future code changes must be reviewed before updating that pin.
- Output artifacts are retained for 30 days. Download important evidence for long-term preservation. Configuration files and credentials are excluded.

The workflow is installed on this fork's default branch. The bounty contribution remains on `feat/voller-attention-tiles-okf`.

On 13 September 2026, live run 34774454331 attempt 3 created an agent and imported all 67 mapped records with zero failures. Export then failed because the runner requested an output folder outside Memanto's allowed directory. The corrected runner now exports in the approved default directory and copies the completed bundle into evidence. It also prints redacted command errors directly in the job log. The corrected full live run 34781697137 subsequently passed both complete-data comparisons. Its first-agent recall was 6/8 and second-agent recall was 8/8, so the strict live job failed. The first two questions missed Attention Display and AI Fisherman even though both records were preserved. Timing and the additional import-wrapper text are possible explanations, not established causes. Diagnostic run 34784846111 subsequently measured immediate recall at 7/8 and 5/8, followed by 8/8 on both agents after complete export verification. It preserved both full exports and retained all early misses, so its strict live job failed. The new v3 runner gates scoring on two consecutive complete exports and then scores each question once; export visibility is not a guarantee of semantic quality. Its full local suite passed 990 tests with 24 skipped. The v3 runner awaits a fresh live service run.

The saved key was available in that run. No additional key setup is needed unless it expires, is revoked or needs rotation. The bounty has not been submitted. Passing these tests does not replace the required live demo video, public showcase, upstream PR and BountyHub claim.

References: [GitHub manual workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow), [GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets), [challenge requirements](https://github.com/moorcheh-ai/memanto/issues/1609).

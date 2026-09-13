# Voller test setup

This repository has a reusable workflow for the reviewed Attention Tiles entry. A new manual run includes the local checks and the real Moorcheh migration. There is no mode selector.

## Start the full test

Open [Voller portable memory tests](https://github.com/jaonnvoller-ai/memanto/actions/workflows/voller-tests.yml), refresh the page, choose **Run workflow**, leave branch **main** selected and press the green **Run workflow** button.

Start a new run from the workflow page. Re-running an older local-only run uses that run's older workflow definition.

## If the run reports a missing key

1. On your signed-in phone, open [Moorcheh API keys](https://console.moorcheh.ai/api-keys) and create a dedicated key for the Voller test runner.
2. Open [this repository's Actions secrets](https://github.com/jaonnvoller-ai/memanto/settings/secrets/actions), choose **New repository secret**, enter the name **MOORCHEH_API_KEY**, paste the key in the secret field and save it. Do not put the key into chat or a source file.
3. Start a new run using the instructions above. If the secret already exists, do not replace it unless it is invalid, expired or needs rotation.

The assistant's connected GitHub tools cannot create repository secrets or start a manual workflow. Those controls remain in your GitHub interface. After a run starts, the assistant can inspect its status and evidence through the GitHub connection.

## What runs

- The local job runs the 11 adapter tests and 20 upstream format tests, then the native local format round trip. It needs no Moorcheh key.
- On a new manual run, the live job follows successful local checks. It imports the 66 public-source records into two new demo agents, exports them and checks exact reconstruction plus eight named-record retrieval probes.
- Push-triggered runs perform local checks only. There is no scheduled or automatic live-service run.
- Each live run uses Moorcheh service credits and creates fresh demo agents. No old agent or source data is deleted.
- Later runs reuse the saved key. Replace it only if it expires, is revoked or needs rotation; this does not guarantee permanent account access.
- The reviewed entry remains pinned to commit `4adeb0ce94502ea8d122ecaade9e1e42f738333a`. Future code changes must be reviewed before updating that pin.
- Output artifacts are retained for 30 days. Download important evidence for long-term preservation. Configuration files and credentials are excluded.

The workflow is installed on this fork's default branch. The bounty contribution remains on `feat/voller-attention-tiles-okf`.

As of 13 September 2026, the completed manual runs 34773321390, 34774119063 and 34774124699 passed local checks and skipped the live job under the earlier workflow definition. A real migration is still unverified, as is the presence of the saved service key. The bounty has not been submitted. Passing these tests does not replace the required live demo video, public showcase, upstream PR and BountyHub claim.

References: [GitHub manual workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow), [GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets), [challenge requirements](https://github.com/moorcheh-ai/memanto/issues/1609).

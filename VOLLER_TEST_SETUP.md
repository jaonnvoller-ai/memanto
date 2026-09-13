# Voller test setup

This repository has a reusable workflow for the reviewed Attention Tiles entry. Google sign-in is not part of the test runner. The live job uses a Moorcheh service key saved in GitHub Actions secrets.

## One setup task remains

1. On a device where your Google account already works, open [Moorcheh API keys](https://console.moorcheh.ai/api-keys) and create a dedicated key for the Voller test runner.
2. Open [this repository's Actions secrets](https://github.com/jaonnvoller-ai/memanto/settings/secrets/actions), choose **New repository secret**, enter the name **MOORCHEH_API_KEY**, paste the key in the secret field and save it. Do not put the key into chat or a source file.
3. Open [Voller portable memory tests](https://github.com/jaonnvoller-ai/memanto/actions/workflows/voller-tests.yml). Choose **Run workflow**, keep branch **main**, select **live** and run it. If GitHub asks you to enable Actions on your fork, enable it once.

The assistant's connected GitHub tools cannot create repository secrets or start a manual workflow. Those two controls remain in your GitHub interface. After a run starts, the assistant can inspect its status and evidence through the GitHub connection.

## What is reusable

- **local** runs the 11 adapter tests and 20 upstream format tests, then the native local format round trip. It needs no Moorcheh key.
- **live** first passes the local checks, then imports the 66 public-source records into two new demo agents, exports them and checks exact reconstruction plus eight named-record retrieval probes.
- Later runs reuse the saved key. Replace the secret only if the key expires, is revoked or needs rotation; this does not guarantee permanent account access.
- Code and workflow remain in GitHub across chats. The reviewed entry is pinned to commit `4adeb0ce94502ea8d122ecaade9e1e42f738333a`. Future code changes must be reviewed before updating that pin.
- Every live run creates two fresh agents and uses Moorcheh service credits. There is no schedule or automatic live run. No old agent or source data is deleted.
- Output artifacts are retained for 30 days. Download important evidence for long-term preservation. Configuration files and credentials are excluded.

The workflow is installed on this fork's default branch for GitHub's manual-run control. The bounty contribution remains on `feat/voller-attention-tiles-okf`.

At preparation time, no live migration has completed, no service key has been configured, and the bounty has not been submitted. The workflow cannot substitute for the required real demo video or guarantee a prize.

References: [GitHub manual workflows](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow), [GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets), [challenge requirements](https://github.com/moorcheh-ai/memanto/issues/1609).

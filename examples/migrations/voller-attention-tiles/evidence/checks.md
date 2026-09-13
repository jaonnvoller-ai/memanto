# Local validation scope

13 September 2026. Memanto pinned to aa3f6f1f4509dd09702679d96ce28cb0f4ac9fe3.

- 31 tests passed: 11 adapter tests, plus upstream tests/test_okf.py and tests/test_migrate.py.
- Ruff check and format check passed for this example.
- Scoped mypy passed for adapter.py, run_demo.py and run_live.py.
- The official CLI dry run mapped 67 records with 0 skipped: 66 artifacts and 1 context.
- The real native exporter ran locally; all 66 source records were restored exactly.
- Only the 66 public-source tiles are included. The original 11 private additions are excluded.

The complete upstream test suite and pre-commit gate have not been run. No live backend migration, semantic recall, demo video, prize submission or payment is represented by these results.

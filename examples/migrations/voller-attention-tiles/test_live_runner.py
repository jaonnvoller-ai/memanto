"""Offline regressions for the live runner; no service credentials are used."""

import subprocess
from pathlib import Path

import pytest
from adapter import build_bundle, restore_bundle
from fastapi import HTTPException
from run_live import export_and_copy, run_cli
from test_adapter import catalog

from memanto.app.services.okf_export_service import OkfExportService
from memanto.cli.migrate.mappers import map_okf
from memanto.cli.migrate.okf_loader import load_okf_bundle


def test_live_export_uses_native_directory_before_collecting(tmp_path, monkeypatch):
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setattr(Path, "home", lambda: home)
    source = tmp_path / "source"
    data = catalog()
    build_bundle(data, source)
    grouped = {}
    for i, row in enumerate(map_okf(load_okf_bundle(source))):
        grouped.setdefault(row["type"], []).append(dict(row, id=f"test-{i}"))
    destination = tmp_path / "workflow-evidence" / "first_export"
    service = OkfExportService()

    # Reproduce the observed failure against the real path validator.
    with pytest.raises(HTTPException, match="output_path must be inside"):
        service.write_okf_bundle("test-agent", grouped, output_dir=destination)

    calls = []

    def command(label, *parts):
        calls.append((label, parts))
        assert "--output" not in parts
        assert parts == (
            "memory",
            "export",
            "--okf",
            "--agent",
            "test-agent",
            "--limit",
            "100",
            "--split",
            "file",
        )
        # Exercise actual serialization at the CLI's default destination.
        service.write_okf_bundle("test-agent", grouped, split="file")

    export_and_copy(command, "04_export", "test-agent", destination)
    assert len(calls) == 1
    assert restore_bundle(destination) == data
    assert restore_bundle(service.exports_dir / "test-agent_okf") == data


def test_failed_command_is_visible_without_exposing_key(tmp_path, monkeypatch, capsys):
    sentinel = "synthetic-test-credential"

    def failed_command(*args, **kwargs):
        return subprocess.CompletedProcess(
            args[0],
            1,
            stdout=f"key={sentinel}\n",
            stderr="::error::export destination rejected\n",
        )

    monkeypatch.setattr(subprocess, "run", failed_command)
    with pytest.raises(RuntimeError, match="04_export failed"):
        run_cli(tmp_path, "04_export", "memory", "export", key=sentinel)
    captured = capsys.readouterr()
    saved = (tmp_path / "04_export.txt").read_text()
    assert sentinel not in captured.err + saved
    assert "[REDACTED]" in captured.err and "[REDACTED]" in saved
    assert "[04_export] ::error::export destination rejected" in captured.err

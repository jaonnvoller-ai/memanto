"""Run the pending real-service migration after configuring Memanto normally.

This command uploads the public-source selection to two fresh demo agents.
It never deletes the source or claims success from a dry run.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

from adapter import (
    build_bundle,
    digest,
    load_catalog,
    restore_bundle,
    select_catalog,
    unpack,
)

PROBES = [
    ("What is the Attention Display concept?", "attention-display"),
    ("What is AI Fisherman designed to do?", "ai-fisherman"),
    ("What is the Find My Fish concept?", "find-my-fish"),
    ("What is Buildwave intended to build?", "buildwave"),
    ("What is the Picture Us app concept?", "picture-us"),
    ("What is the AquaFlight concept?", "aquaflight"),
    ("What is the Ocean Bubbles proposal?", "ocean-bubbles"),
    ("What is Super Punch intended for?", "super-punch"),
]


def source_recall(data: dict, query: str) -> list[str]:
    terms = set(re.findall(r"\w+", query.lower())) - {
        "what",
        "is",
        "the",
        "to",
        "do",
        "a",
        "for",
        "concept",
        "intended",
        "designed",
        "proposal",
    }
    scored = []
    for tile in data["tiles"]:
        aliases = tile.get("aliases") or []
        if not isinstance(aliases, list):
            aliases = []
        names = " ".join(str(value) for value in [tile["title"], tile["id"], *aliases])
        title = set(re.findall(r"\w+", names.lower()))
        summary = set(re.findall(r"\w+", tile["summary"].lower()))
        scored.append((4 * len(terms & title) + len(terms & summary), tile["id"]))
    return [
        identifier
        for score, identifier in sorted(scored, key=lambda pair: (-pair[0], pair[1]))[
            :5
        ]
        if score > 0
    ]


def remote_recall(agent: str, query: str) -> list[str]:
    from memanto.cli.commands._shared import get_client

    result = get_client().recall(agent_id=agent, query=query, limit=5)
    ids = []
    for memory in result.get("memories", []):
        content = memory.get("content", "")
        if not content:
            continue
        try:
            record = unpack(content)
        except (ValueError, KeyError, TypeError):
            continue
        if record["kind"] == "tile":
            ids.append(record["data"]["id"])
    return ids


def main() -> int:
    from memanto.cli.config.manager import ConfigManager

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--upload-public-source", action="store_true")
    args = parser.parse_args()
    if not args.upload_public_source:
        parser.error(
            "Pass --upload-public-source only when ready to upload this selection"
        )
    cfg = ConfigManager()
    if not cfg.get_api_key() and str(cfg.get_backend().value) != "on-prem":
        print(
            "BLOCKED: configure the real Moorcheh service through Memanto first. No upload was attempted."
        )
        return 2
    data = select_catalog(load_catalog(args.source), public_only=True)
    available_ids = {t["id"] for t in data["tiles"]}
    if not all(identifier in available_ids for _, identifier in PROBES):
        raise ValueError(
            "This live probe set requires the supplied Voller public-source snapshot"
        )
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build_bundle(data, output / "source_okf")
    key = cfg.get_api_key()

    def command(label: str, *parts: str) -> None:
        proc = subprocess.run(
            [sys.executable, "-m", "memanto.cli.main", *parts],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        transcript = proc.stdout + proc.stderr
        if key:
            transcript = transcript.replace(key, "[REDACTED]")
        (output / f"{label}.txt").write_text(transcript, encoding="utf-8")
        if proc.returncode:
            raise RuntimeError(f"{label} failed; review its saved log")
        print(f"Completed {label}", flush=True)

    suffix = uuid.uuid4().hex[:12]
    first, second = f"voller-portable-{suffix}-a", f"voller-portable-{suffix}-b"
    baseline: list[dict[str, Any]] = [
        {"query": q, "expected_id": target, "source_top5": source_recall(data, q)}
        for q, target in PROBES
    ]
    command("01_create_first", "agent", "create", first)
    command("02_preview", "migrate", "okf", str(output / "source_okf"), "--dry-run")
    command("03_import", "migrate", "okf", str(output / "source_okf"), "--agent", first)
    for probe in baseline:
        probe["first_memanto_top5"] = remote_recall(first, probe["query"])
    command(
        "04_export",
        "memory",
        "export",
        "--okf",
        "--agent",
        first,
        "--limit",
        "100",
        "--split",
        "file",
        "--output",
        str(output / "first_export"),
    )
    if digest(restore_bundle(output / "first_export")) != digest(data):
        raise AssertionError(
            "First real-service export did not preserve all selected fields"
        )
    command("05_create_second", "agent", "create", second)
    command(
        "06_reimport", "migrate", "okf", str(output / "first_export"), "--agent", second
    )
    for probe in baseline:
        probe["second_memanto_top5"] = remote_recall(second, probe["query"])
    command(
        "07_export_again",
        "memory",
        "export",
        "--okf",
        "--agent",
        second,
        "--limit",
        "100",
        "--split",
        "file",
        "--output",
        str(output / "second_export"),
    )
    if digest(restore_bundle(output / "second_export")) != digest(data):
        raise AssertionError(
            "Second real-service export did not preserve all selected fields"
        )
    scores = {
        field: sum(p["expected_id"] in p[field] for p in baseline)
        for field in ("source_top5", "first_memanto_top5", "second_memanto_top5")
    }
    report = {
        "agents_created": [first, second],
        "selected_tiles": len(data["tiles"]),
        "data_round_trip_passed": True,
        "retrieval_hits_out_of_8": scores,
        "probes": baseline,
        "probe_limit": "Eight named-record retrieval probes; not a general answer-quality or reasoning benchmark",
        "competition_entry_complete": False,
    }
    (output / "live_validation.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        json.dumps(
            {"data_round_trip_passed": True, "retrieval_hits_out_of_8": scores},
            indent=2,
        )
    )
    return 0 if all(value == 8 for value in scores.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())

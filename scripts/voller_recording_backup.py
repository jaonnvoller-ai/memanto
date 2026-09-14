"""Read and verify exactly two existing public demo copies. Never deletes data."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

AGENTS = ("voller-portable-8e5ffe7a173f-a", "voller-portable-8e5ffe7a173f-b")
SOURCE_HASH = "b17e0beea4e41398da496e3b78d4625ee4c149fd33a14c292247fa7d64d7e5cc"


def read_all(client: Any, namespace: str) -> list[dict[str, Any]]:
    if namespace not in {"memanto_agent_" + a for a in AGENTS}:
        raise ValueError("Outside the exact proposed demo pair")
    records: list[dict[str, Any]] = []
    token = None
    seen: set[str] = set()
    for _ in range(10):
        page = client.documents.fetch_text_data(
            namespace_name=namespace, limit=100, next_token=token
        )
        items, pagination = page.get("items"), page.get("pagination")
        if not isinstance(items, list) or not isinstance(pagination, dict):
            raise ValueError("Incomplete snapshot response")
        if any(not isinstance(item, dict) for item in items):
            raise ValueError("Invalid snapshot record")
        records.extend(items)
        if pagination.get("has_more") is False:
            return records
        token = pagination.get("next_token")
        if pagination.get("has_more") is not True or not token or token in seen:
            raise ValueError("Pagination did not prove completeness")
        seen.add(token)
    raise ValueError("Snapshot exceeded pagination limit")


def snapshot(entry: Path, output: Path) -> None:
    sys.path.insert(0, str(entry.resolve()))
    from adapter import digest, restore_contents
    from moorcheh_sdk import MoorchehClient

    from memanto.app.services.memory_read_service import MemoryReadService
    from memanto.app.services.okf_export_service import OkfExportService

    key = os.environ.get("MOORCHEH_API_KEY")
    if not key:
        raise ValueError("The existing repository service secret is required")
    snapshots: dict[str, dict[str, Any]] = {}
    with MoorchehClient(api_key=key) as client:
        parser = MemoryReadService(client)
        renderer = OkfExportService()
        for agent in AGENTS:
            namespace = "memanto_agent_" + agent
            items = sorted(read_all(client, namespace), key=lambda r: str(r.get("id")))
            if len(items) != 67 or any(r.get("is_summary") for r in items):
                raise ValueError("Demo copy contains unexpected records")
            formatted = [parser._format_memory_item(item) for item in items]
            ids = [r.get("id") for r in formatted]
            if len(set(ids)) != 67 or any(
                not isinstance(i, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", i)
                for i in ids
            ):
                raise ValueError("Demo copy contains invalid memory IDs")
            if any(r.get("agent_id") != agent for r in formatted):
                raise ValueError("Unexpected agent in demo copy")
            if (
                digest(restore_contents([r["content"] for r in formatted]))
                != SOURCE_HASH
            ):
                raise ValueError("Demo copy differs from the public 66-tile catalogue")
            raw = json.dumps(items, indent=2, ensure_ascii=False)
            if key in raw:
                raise ValueError("Snapshot contains the service credential")
            hashes = {
                r["id"]: hashlib.sha256(
                    renderer._render_okf_doc(r, r["type"]).encode()
                ).hexdigest()
                for r in formatted
            }
            snapshots[namespace] = {"raw": raw, "memory_sha256": hashes}
    # Save only after BOTH copies have proved identical to the public catalogue.
    output.mkdir(parents=True, exist_ok=False)
    report: dict[str, Any] = {
        "source_sha256": SOURCE_HASH,
        "read_only": True,
        "cloud_write_attempted": False,
        "snapshot_grants_deletion_authority": False,
        "proposed_targets": [],
    }
    for namespace, data in snapshots.items():
        (output / f"{namespace}.json").write_text(data["raw"], encoding="utf-8")
        report["proposed_targets"].append(
            {
                "namespace": namespace,
                "documents": 67,
                "public_tiles": 66,
                "snapshot_sha256": hashlib.sha256(data["raw"].encode()).hexdigest(),
                "memory_sha256": data["memory_sha256"],
            }
        )
        print(f"Verified public snapshot: {namespace}; 67 records / 66 tiles")
    (output / "backup_manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Both backups verified. No cloud data changed or deleted.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--entry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        snapshot(args.entry, args.output)
    except Exception as exc:
        # Avoid copying service error bodies into a public workflow log.
        print(f"Public demo snapshot stopped: {type(exc).__name__}. Nothing deleted.")
        raise SystemExit(1)

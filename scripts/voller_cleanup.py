"""One-off removal of exactly the two cloud test copies approved by Jaon.

Prepare saves fresh snapshots. Purge requires a successful artifact upload,
revalidates both live namespaces, and stops if anything has changed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Any

AGENTS = ("voller-portable-054a48145260-a", "voller-portable-054a48145260-b")
TARGETS = tuple("memanto_agent_" + agent for agent in AGENTS)
SOURCE_HASH = "b17e0beea4e41398da496e3b78d4625ee4c149fd33a14c292247fa7d64d7e5cc"


def digest(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode()).hexdigest()


def namespace_map(client: Any) -> dict[str, dict[str, Any]]:
    rows = client.namespaces.list()["namespaces"]
    if not isinstance(rows, list):
        raise ValueError("Invalid namespace list")
    result = {row["namespace_name"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate namespaces in response")
    return result


def fetch_complete(client: Any, namespace: str) -> list[dict[str, Any]]:
    if namespace not in TARGETS:
        raise ValueError("Namespace is outside the approved cleanup")
    items: list[dict[str, Any]] = []
    token = None
    seen: set[str] = set()
    for _ in range(10):
        result = client.documents.fetch_text_data(
            namespace_name=namespace, limit=100, next_token=token
        )
        page = result.get("items")
        pagination = result.get("pagination")
        if not isinstance(page, list) or not isinstance(pagination, dict):
            raise ValueError("Incomplete namespace response")
        if any(not isinstance(item, dict) for item in page):
            raise ValueError("Malformed document")
        items.extend(page)
        if pagination.get("has_more") is False:
            return sorted(items, key=lambda item: str(item.get("id", "")))
        token = pagination.get("next_token")
        if pagination.get("has_more") is not True or not token or token in seen:
            raise ValueError("Pagination did not prove a complete snapshot")
        seen.add(token)
    raise ValueError("Snapshot exceeded pagination limit")


def verify_records(
    client: Any, namespace: str, items: list[dict[str, Any]], expected: dict[str, str]
) -> None:
    from adapter import digest as source_digest
    from adapter import restore_contents
    from memanto.app.services.memory_read_service import MemoryReadService
    from memanto.app.services.okf_export_service import OkfExportService

    if namespace not in TARGETS or len(expected) != 67 or len(items) != 67:
        raise ValueError("Unexpected namespace or document count; nothing removed")
    ids = [item.get("id") for item in items]
    if set(ids) != set(expected) or len(set(ids)) != len(ids):
        raise ValueError("Live document IDs differ from the archived test copy")
    parser = MemoryReadService(client)
    renderer = OkfExportService()
    contents = []
    for item in items:
        if item.get("is_summary"):
            raise ValueError("Unexpected summary document")
        record = parser._format_memory_item(item)
        if record.get("agent_id") != namespace.removeprefix("memanto_agent_"):
            raise ValueError("Document belongs to an unexpected agent")
        rendered = renderer._render_okf_doc(record, record["type"])
        if hashlib.sha256(rendered.encode()).hexdigest() != expected[item["id"]]:
            raise ValueError("Live memory differs from its archived OKF record")
        contents.append(record["content"])
    if source_digest(restore_contents(contents)) != SOURCE_HASH:
        raise ValueError("Source reconstruction differs from the saved catalogue")


def prepare(client: Any, output: Path, manifest: dict[str, Any]) -> None:
    if set(manifest["namespaces"]) != set(TARGETS):
        raise ValueError("Manifest does not identify exactly the approved pair")
    output.mkdir(parents=True, exist_ok=False)
    current = namespace_map(client)
    snapshots: dict[str, dict[str, Any]] = {}
    for namespace in TARGETS:
        if namespace not in current:
            snapshots[namespace] = {"absent": True}
            continue
        if current[namespace].get("type") != "text":
            raise ValueError("Approved test namespace is no longer text storage")
        items = fetch_complete(client, namespace)
        verify_records(client, namespace, items, manifest["namespaces"][namespace])
        filename = namespace + ".json"
        (output / filename).write_text(json.dumps(items, indent=2), encoding="utf-8")
        snapshots[namespace] = {
            "absent": False,
            "filename": filename,
            "items_sha256": digest(items),
            "documents": len(items),
        }
        print(f"Verified and backed up {namespace}: {len(items)} documents", flush=True)
    (output / "prepared.json").write_text(
        json.dumps({"namespaces": snapshots, "source_sha256": SOURCE_HASH}, indent=2),
        encoding="utf-8",
    )


def purge(
    client: Any, output: Path, manifest: dict[str, Any], artifact_id: str
) -> None:
    if not artifact_id.isdecimal() or int(artifact_id) <= 0:
        raise ValueError("Fresh backup must be uploaded successfully before deletion")
    state = json.loads((output / "prepared.json").read_text())
    if set(state["namespaces"]) != set(TARGETS):
        raise ValueError("Backup state is outside the approved cleanup")
    if set(manifest["namespaces"]) != set(TARGETS):
        raise ValueError("Manifest is outside the approved cleanup")
    current = namespace_map(client)
    to_delete = []
    # Recheck both before deleting either. Absent targets are an idempotent no-op.
    for namespace in TARGETS:
        if namespace not in current:
            continue
        snapshot = state["namespaces"][namespace]
        if snapshot.get("absent") or current[namespace].get("type") != "text":
            raise ValueError("Namespace appeared or changed after backup")
        if snapshot["filename"] != namespace + ".json":
            raise ValueError("Unexpected backup filename")
        backup = json.loads((output / snapshot["filename"]).read_text())
        if digest(backup) != snapshot["items_sha256"]:
            raise ValueError("Saved snapshot changed")
        items = fetch_complete(client, namespace)
        verify_records(client, namespace, items, manifest["namespaces"][namespace])
        if digest(items) != snapshot["items_sha256"]:
            raise ValueError("Cloud data changed after backup; nothing removed")
        to_delete.append(namespace)
    result: dict[str, Any] = {
        "backup_artifact_id": artifact_id,
        "approved_targets": list(TARGETS),
        "delete_requests_completed": [],
        "capacity_confirmed": False,
    }
    result_path = output / "cleanup_result.json"

    def save() -> None:
        result_path.write_text(json.dumps(result, indent=2), encoding="utf-8")

    save()
    for namespace in to_delete:
        client.namespaces.delete(namespace)
        result["delete_requests_completed"].append(namespace)
        save()
        print(f"Removed approved test namespace: {namespace}", flush=True)
    for attempt in range(30):
        remaining = namespace_map(client)
        result["remaining_namespace_count"] = len(remaining)
        result["targets_still_present"] = [n for n in TARGETS if n in remaining]
        result["capacity_confirmed"] = (
            not result["targets_still_present"] and len(remaining) <= 3
        )
        save()
        if result["capacity_confirmed"]:
            print(
                "Confirmed at least two free namespace slots on the five-slot plan.",
                flush=True,
            )
            return
        if attempt < 29:
            time.sleep(2)
    raise TimeoutError(
        "Deletion or quota release is still pending; live test was not started"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=("prepare", "purge"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--entry", type=Path, required=True)
    parser.add_argument("--backup-artifact-id", default="")
    args = parser.parse_args()
    sys.path.insert(0, str(args.entry.resolve()))
    manifest = json.loads(
        Path(__file__).with_name("voller_cleanup_manifest.json").read_text()
    )
    from moorcheh_sdk import MoorchehClient

    key = os.environ.get("MOORCHEH_API_KEY")
    if not key:
        raise ValueError("The existing repository service secret is required")
    logging.getLogger().setLevel(logging.WARNING)
    with MoorchehClient(api_key=key) as client:
        if args.phase == "prepare":
            prepare(client, args.output, manifest)
        else:
            purge(client, args.output, manifest, args.backup_artifact_id)


if __name__ == "__main__":
    main()

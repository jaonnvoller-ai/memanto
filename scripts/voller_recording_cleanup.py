"""Remove only Jaon's explicitly approved, freshly backed-up recording pair."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from voller_recording_backup import AGENTS, SOURCE_HASH, read_all

TARGETS = tuple("memanto_agent_" + agent for agent in AGENTS)


def canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def namespaces(client: Any) -> dict[str, dict[str, Any]]:
    rows = client.namespaces.list()["namespaces"]
    if not isinstance(rows, list):
        raise ValueError("Invalid namespace response")
    result = {row["namespace_name"]: row for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate namespace names")
    return result


def purge(client: Any, backup: Path, artifact_id: str) -> None:
    if not artifact_id.isdecimal() or int(artifact_id) <= 0:
        raise ValueError("A successful fresh backup artifact upload is required")
    manifest = json.loads((backup / "backup_manifest.json").read_text())
    entries = manifest["proposed_targets"]
    if len(entries) != 2 or {r["namespace"] for r in entries} != set(TARGETS):
        raise ValueError("Backup manifest is outside the approved pair")
    if manifest["source_sha256"] != SOURCE_HASH:
        raise ValueError("Backup is not the approved public catalogue")
    current = namespaces(client)
    to_delete = []
    # Revalidate BOTH copies before issuing the first delete request.
    for entry in entries:
        namespace = entry["namespace"]
        path = backup / f"{namespace}.json"
        if path.is_symlink():
            raise ValueError("Linked backup is not allowed")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != entry["snapshot_sha256"]:
            raise ValueError("Backup file changed")
        saved = json.loads(raw)
        if entry["documents"] != 67 or entry["public_tiles"] != 66 or len(saved) != 67:
            raise ValueError("Unexpected backup record count")
        if namespace not in current:
            continue
        if current[namespace].get("type") != "text":
            raise ValueError("Namespace type changed")
        live = sorted(read_all(client, namespace), key=lambda r: str(r.get("id")))
        if canonical(live) != canonical(saved):
            raise ValueError("Cloud copy changed since its fresh backup")
        to_delete.append(namespace)
    result: dict[str, Any] = {
        "approved_targets": list(TARGETS),
        "backup_artifact_id": artifact_id,
        "delete_requests_completed": [],
        "capacity_confirmed": False,
    }
    path = backup / "cleanup_result.json"

    def save() -> None:
        path.write_text(json.dumps(result, indent=2) + "\n")

    save()
    for namespace in to_delete:
        client.namespaces.delete(namespace)
        result["delete_requests_completed"].append(namespace)
        save()
        print("Removed approved backed-up demo copy: " + namespace, flush=True)
    for attempt in range(30):
        remaining = namespaces(client)
        result["targets_still_present"] = [n for n in TARGETS if n in remaining]
        result["remaining_namespace_count"] = len(remaining)
        result["capacity_confirmed"] = (
            not result["targets_still_present"] and len(remaining) <= 3
        )
        save()
        if result["capacity_confirmed"]:
            print("Confirmed two free cloud slots for the recording.", flush=True)
            return
        if attempt < 29:
            time.sleep(2)
    raise TimeoutError("Capacity release is pending; do not start a new import")


if __name__ == "__main__":
    from moorcheh_sdk import MoorchehClient

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backup", type=Path, required=True)
    parser.add_argument("--backup-artifact-id", required=True)
    args = parser.parse_args()
    key = os.environ.get("MOORCHEH_API_KEY")
    if not key:
        raise SystemExit("Existing service credential is required")
    try:
        with MoorchehClient(api_key=key) as client:
            purge(client, args.backup, args.backup_artifact_id)
    except Exception as exc:
        print(
            f"Approved cleanup stopped: {type(exc).__name__}; review cleanup_result.json"
        )
        raise SystemExit(1)

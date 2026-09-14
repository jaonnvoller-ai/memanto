import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import voller_recording_cleanup as cleanup  # noqa: E402


def fixture(backup):
    records = sorted(
        [{"id": str(i), "data": "fixture"} for i in range(67)],
        key=lambda row: row["id"],
    )
    entries = []
    for namespace in cleanup.TARGETS:
        raw = json.dumps(records)
        (backup / f"{namespace}.json").write_text(raw)
        entries.append(
            {
                "namespace": namespace,
                "documents": 67,
                "public_tiles": 66,
                "snapshot_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            }
        )
    (backup / "backup_manifest.json").write_text(
        json.dumps({"proposed_targets": entries, "source_sha256": cleanup.SOURCE_HASH})
    )
    return records


def client_for(records, changed=False):
    existing = set(cleanup.TARGETS) | {"unrelated"}
    deleted = []

    def delete(namespace):
        deleted.append(namespace)
        existing.remove(namespace)

    def fetch_text_data(namespace_name, **kwargs):
        rows = records
        if changed and namespace_name == cleanup.TARGETS[1]:
            rows = records[:-1]
        return {"items": rows, "pagination": {"has_more": False}}

    client = SimpleNamespace(
        namespaces=SimpleNamespace(
            list=lambda: {
                "namespaces": [{"namespace_name": n, "type": "text"} for n in existing]
            },
            delete=delete,
        ),
        documents=SimpleNamespace(fetch_text_data=fetch_text_data),
    )
    return client, deleted


def test_cleanup_requires_uploaded_backup(tmp_path):
    records = fixture(tmp_path)
    client, deleted = client_for(records)
    with pytest.raises(ValueError, match="upload"):
        cleanup.purge(client, tmp_path, "")
    assert deleted == []


def test_second_copy_changed_prevents_both_deletes(tmp_path):
    records = fixture(tmp_path)
    client, deleted = client_for(records, changed=True)
    with pytest.raises(ValueError, match="changed"):
        cleanup.purge(client, tmp_path, "123")
    assert deleted == []


def test_cleanup_rejects_an_unapproved_target(tmp_path):
    records = fixture(tmp_path)
    client, deleted = client_for(records)
    path = tmp_path / "backup_manifest.json"
    manifest = json.loads(path.read_text())
    manifest["proposed_targets"][1]["namespace"] = "unrelated"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="outside"):
        cleanup.purge(client, tmp_path, "123")
    assert deleted == []


def test_cleanup_removes_exact_pair_and_preserves_other_namespace(tmp_path):
    records = fixture(tmp_path)
    client, deleted = client_for(records)
    cleanup.purge(client, tmp_path, "123")
    assert deleted == list(cleanup.TARGETS)
    assert set(cleanup.namespaces(client)) == {"unrelated"}
    result = json.loads((tmp_path / "cleanup_result.json").read_text())
    assert result["capacity_confirmed"] is True

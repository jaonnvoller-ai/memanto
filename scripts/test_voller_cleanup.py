"""Safety checks for the explicitly approved one-off cleanup."""

import copy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import voller_cleanup as cleanup


@pytest.fixture
def case(tmp_path, monkeypatch):
    from memanto.cli.migrate.okf_loader import load_okf_bundle

    root = Path(__file__).resolve().parents[1]
    # In CI the reviewed entry is checked out at the workspace root; locally it
    # is the sibling memanto-entry directory.
    entry = root / "examples/migrations/voller-attention-tiles"
    if not entry.exists():
        entry = root.parent / "memanto-entry/examples/migrations/voller-attention-tiles"
    if not entry.exists():
        entry = root.parent / "examples/migrations/voller-attention-tiles"
    monkeypatch.syspath_prepend(str(entry))
    rows = load_okf_bundle(entry / "sample-cloud-okf")["memories"]
    records = {}
    expected = {}
    for namespace, agent in zip(cleanup.TARGETS, cleanup.AGENTS, strict=True):
        docs = []
        hashes = {}
        for row in rows:
            extra = row["x_memanto"]
            text = f"[{row['type'].upper()}] {row['title']}\n\n{row['body'].strip()}"
            tags = row.get("tags") or []
            if tags:
                text += "\n\nTags: " + ", ".join(tags)
            docs.append(
                {
                    "id": extra["id"],
                    "text": text,
                    "memory_type": row["type"],
                    "agent_id": agent,
                    "tags": ",".join(tags),
                    "source_ref": row.get("resource"),
                    "created_at": row.get("extra", {}).get("generated", {}).get("at"),
                    **extra,
                }
            )
            path = entry / "sample-cloud-okf" / row["source_path"]
            hashes[extra["id"]] = hashlib.sha256(path.read_bytes()).hexdigest()
        records[namespace] = docs
        expected[namespace] = hashes
    live = set(cleanup.TARGETS) | {"unrelated-user-agent"}
    client = SimpleNamespace(namespaces=Mock(), documents=Mock())
    client.namespaces.list.side_effect = lambda: {
        "namespaces": [{"namespace_name": n, "type": "text"} for n in sorted(live)]
    }
    client.namespaces.delete.side_effect = lambda name: live.remove(name)
    client.documents.fetch_text_data.side_effect = lambda **kw: {
        "items": copy.deepcopy(records[kw["namespace_name"]]),
        "pagination": {"has_more": False},
    }
    return SimpleNamespace(
        client=client,
        records=records,
        live=live,
        output=tmp_path / "backup",
        manifest={"namespaces": expected},
    )


def test_only_approved_pair_removed_after_uploaded_verified_backup(case):
    cleanup.prepare(case.client, case.output, case.manifest)
    case.client.namespaces.delete.assert_not_called()
    cleanup.purge(case.client, case.output, case.manifest, "123456")
    assert [c.args[0] for c in case.client.namespaces.delete.call_args_list] == list(
        cleanup.TARGETS
    )
    assert case.live == {"unrelated-user-agent"}
    assert json.loads((case.output / "cleanup_result.json").read_text())[
        "capacity_confirmed"
    ]


def test_changed_second_copy_prevents_deleting_either(case):
    cleanup.prepare(case.client, case.output, case.manifest)
    case.records[cleanup.TARGETS[1]][0]["text"] += "\nnew information"
    with pytest.raises(ValueError, match="differs"):
        cleanup.purge(case.client, case.output, case.manifest, "123456")
    case.client.namespaces.delete.assert_not_called()


def test_added_record_refuses_prepare(case):
    case.records[cleanup.TARGETS[0]].append({"id": "new", "text": "new information"})
    with pytest.raises(ValueError, match="count"):
        cleanup.prepare(case.client, case.output, case.manifest)
    assert not (case.output / "prepared.json").exists()
    case.client.namespaces.delete.assert_not_called()


def test_no_uploaded_backup_no_delete(case):
    cleanup.prepare(case.client, case.output, case.manifest)
    with pytest.raises(ValueError, match="uploaded"):
        cleanup.purge(case.client, case.output, case.manifest, "")
    case.client.namespaces.delete.assert_not_called()


def test_changed_saved_backup_no_delete(case):
    cleanup.prepare(case.client, case.output, case.manifest)
    (case.output / (cleanup.TARGETS[0] + ".json")).write_text("[]")
    with pytest.raises(ValueError, match="snapshot changed"):
        cleanup.purge(case.client, case.output, case.manifest, "123456")
    case.client.namespaces.delete.assert_not_called()


def test_already_absent_pair_is_safe_noop(case):
    case.live.difference_update(cleanup.TARGETS)
    cleanup.prepare(case.client, case.output, case.manifest)
    cleanup.purge(case.client, case.output, case.manifest, "123456")
    case.client.namespaces.delete.assert_not_called()
    case.client.documents.fetch_text_data.assert_not_called()


def test_pagination_cycle_is_rejected(case):
    case.client.documents.fetch_text_data.side_effect = lambda **kw: {
        "items": [],
        "pagination": {"has_more": True, "next_token": "same"},
    }
    with pytest.raises(ValueError, match="Pagination"):
        cleanup.prepare(case.client, case.output, case.manifest)
    case.client.namespaces.delete.assert_not_called()


def test_unauthorised_namespace_is_never_read(case):
    with pytest.raises(ValueError, match="outside"):
        cleanup.fetch_complete(case.client, "unrelated-user-agent")
    case.client.documents.fetch_text_data.assert_not_called()


def test_pending_deletion_does_not_claim_capacity(case, monkeypatch):
    cleanup.prepare(case.client, case.output, case.manifest)
    case.client.namespaces.delete.side_effect = None
    monkeypatch.setattr(cleanup.time, "sleep", lambda _: None)
    with pytest.raises(TimeoutError, match="pending"):
        cleanup.purge(case.client, case.output, case.manifest, "123456")
    assert not json.loads((case.output / "cleanup_result.json").read_text())[
        "capacity_confirmed"
    ]

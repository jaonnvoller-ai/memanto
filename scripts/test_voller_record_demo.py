import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

spec = importlib.util.spec_from_file_location(
    "recorder", Path(__file__).with_name("voller_record_demo.py")
)
assert spec is not None and spec.loader is not None
recorder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(recorder)


def test_screen_redacts_split_credential_and_terminal_controls():
    target = io.StringIO()
    screen = recorder.ScreenText(target, "test-secret")
    screen.write("value=test-")
    screen.flush()
    assert target.getvalue() == ""
    screen.write("secret\n\x1b[31mresult\x1b[0m\n")
    screen.finish()
    assert target.getvalue() == "value=[REDACTED]\nresult\n"


def test_preflight_full_account_makes_no_mutations(monkeypatch, tmp_path):
    class Client:
        def __init__(self, **kwargs):
            self.namespaces = SimpleNamespace(
                list=lambda: {
                    "namespaces": [{"namespace_name": f"other-{i}"} for i in range(5)]
                }
            )

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

    monkeypatch.setitem(
        sys.modules, "moorcheh_sdk", SimpleNamespace(MoorchehClient=Client)
    )
    monkeypatch.setenv("MOORCHEH_API_KEY", "test-secret")
    path = tmp_path / "capacity.json"
    assert recorder.preflight(path) == 3
    result = json.loads(path.read_text())
    assert result["cloud_write_attempted"] is False
    assert result["two_free_slots"] is False
    assert result["existing_demo_namespaces"] == []


def test_scan_rejects_secret_and_symlink(monkeypatch, tmp_path):
    import pytest

    monkeypatch.setenv("MOORCHEH_API_KEY", "test-secret")
    path = tmp_path / "log.txt"
    path.write_text("test-secret")
    with pytest.raises(ValueError, match="credential"):
        recorder.scan(tmp_path)
    path.unlink()
    path.symlink_to("/tmp/nonexistent")
    with pytest.raises(ValueError, match="linked"):
        recorder.scan(tmp_path)

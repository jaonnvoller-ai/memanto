"""Capture a real xterm session; never turn historical logs into a demo video."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time


class ScreenText(io.TextIOBase):
    """Redact before text reaches the terminal, including split writes."""

    def __init__(self, target, key=""):
        self.target, self.key, self.pending = target, key, ""

    def write(self, value):
        self.pending += value
        while "\n" in self.pending:
            line, self.pending = self.pending.split("\n", 1)
            self.emit(line + "\n")
        return len(value)

    def emit(self, value):
        if self.key:
            value = value.replace(self.key, "[REDACTED]")
        value = re.sub(r"\x1b\][^\x07]*(?:\x07|\x1b\\)", "", value)
        value = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", value)
        self.target.write("".join(c for c in value if c.isprintable() or c in "\n\t"))
        self.target.flush()

    def flush(self):
        # Keep incomplete lines until finish so a split secret cannot leak.
        self.target.flush()

    def finish(self):
        self.emit(self.pending)
        self.pending = ""


def preflight(output: Path) -> int:
    """Read namespace metadata only. No deletion, plan changes or imports."""
    from moorcheh_sdk import MoorchehClient

    key = os.environ.get("MOORCHEH_API_KEY")
    if not key:
        raise ValueError("MOORCHEH_API_KEY repository secret is missing")
    with MoorchehClient(api_key=key) as client:
        rows = client.namespaces.list()["namespaces"]
    if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
        raise ValueError("Namespace capacity response is invalid")
    names = [r["namespace_name"] for r in rows]
    if len(set(names)) != len(names):
        raise ValueError("Namespace capacity response contains duplicate names")
    # Five slots is the previously observed account limit. Never assume an upgrade.
    ready = len(rows) <= 3
    report = {
        "namespace_count": len(rows),
        "known_plan_slots": 5,
        "two_free_slots": ready,
        "cloud_write_attempted": False,
        "existing_demo_namespaces": [
            n for n in names if re.fullmatch(r"memanto_agent_voller-portable-[a-f0-9]{12}-[ab]", n)
        ],
        "note": "No namespaces deleted. Existing copies require separate cleanup approval.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)
    if not ready:
        print("BLOCKED: this recording needs two free namespace slots. No upload attempted.")
    return 0 if ready else 3


def show_sample(folder: Path):
    paths = sorted((folder / "memories").rglob("*.md"))
    if not paths:
        raise ValueError("No real exported Markdown records found")
    sample = next((p for p in paths if "AI Fisherman" in p.read_text()), paths[0])
    print("\nACTUAL EXPORTED MARKDOWN: " + str(sample))
    print("\n".join(sample.read_text().splitlines()[:24]))
    time.sleep(4)


def session(entry: Path, output: Path, mode: str) -> int:
    while not (output / "capture-started").exists():
        time.sleep(0.1)
    sys.path.insert(0, str(entry))
    source = entry / "source_public.json"
    data = json.loads(source.read_text())
    print("VOLLER ATTENTION TILES | MEMANTO + OKF")
    print("Automated real terminal capture | " + time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()))
    print("Mode: " + ("LIVE CLOUD MIGRATION" if mode == "cloud" else "LOCAL FORMAT ONLY - no cloud migration"))
    print(f"Saved public catalogue: {len(data['tiles'])} tiles")
    print("Finding relevant context: month, weather and tide can change a fishing answer.")
    print("These are concept records, not proof of physical or healing performance.")
    for tile in data["tiles"]:
        if tile["id"] in ("attention-display", "ai-fisherman"):
            print(json.dumps({k: tile[k] for k in ("id", "title", "summary")}, ensure_ascii=False))
    time.sleep(5)
    evidence = output / "evidence"
    if mode == "local":
        import run_demo
        print("\n$ python run_demo.py source_public.json evidence")
        run_demo.execute(source, evidence, True)
        show_sample(evidence / "exported_okf")
        code = 0
        print("LOCAL FORMAT RECORDING COMPLETE. This is not the required cloud demonstration.")
    else:
        import run_live
        original = run_live.run_cli

        def visible_cli(folder, label, *parts, key=None):
            print("\n$ memanto " + shlex.join(parts), flush=True)
            original(folder, label, *parts, key=key)
            print((folder / f"{label}.txt").read_text(), flush=True)

        run_live.run_cli = visible_cli
        sys.argv = ["run_live.py", str(source), str(evidence), "--upload-public-source"]
        code = run_live.main()
        if (evidence / "second_export").exists():
            show_sample(evidence / "second_export")
        if (evidence / "live_validation.json").exists():
            result = json.loads((evidence / "live_validation.json").read_text())
            print("\nRESULTS FROM THIS RECORDING:")
            print(json.dumps({k: result[k] for k in ("selected_tiles", "data_round_trip_passed", "retrieval_hits_out_of_8")}, indent=2))
        print("PASS" if code == 0 else "FAILED: review this run's evidence")
        print("Eight named-record lookups; no general answer-quality or savings claim.")
        print("Custom-catalogue eligibility and prize approval remain unconfirmed.")
    time.sleep(6)
    return code


def record(entry: Path, output: Path, mode: str) -> int:
    for binary in ("Xvfb", "xterm", "ffmpeg", "ffprobe", "xdpyinfo"):
        if not shutil.which(binary):
            raise ValueError(f"Recorder dependency missing: {binary}")
    output.mkdir(parents=True, exist_ok=False)
    env = {**os.environ, "DISPLAY": ":99", "PYTHONUNBUFFERED": "1", "TERM": "xterm"}
    recorder_env = {k: v for k, v in env.items() if k != "MOORCHEH_API_KEY"}
    video = output / f"voller-{mode}-demo.mp4"
    processes = []
    started = time.time()
    try:
        with (output / "xvfb.log").open("w") as log:
            xvfb = subprocess.Popen(["Xvfb", ":99", "-screen", "0", "1280x720x24", "-nolisten", "tcp"], env=recorder_env, stdout=log, stderr=log)
        processes.append(xvfb)
        for _ in range(50):
            if xvfb.poll() is not None:
                raise RuntimeError("Virtual display failed to start")
            if subprocess.run(["xdpyinfo"], env=recorder_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
                break
            time.sleep(0.1)
        else:
            raise TimeoutError("Virtual display did not become ready")
        command = ["xterm", "-geometry", "110x34+0+0", "-fa", "DejaVu Sans Mono", "-fs", "13", "-bg", "#111827", "-fg", "#f3f4f6", "-sb", "-rightbar", "-title", "Voller real Memanto demonstration", "-e", sys.executable, str(Path(__file__).resolve()), "session", "--mode", mode, "--entry", str(entry), "--output", str(output)]
        terminal = subprocess.Popen(command, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        processes.append(terminal)
        with (output / "ffmpeg.log").open("w") as log:
            capture = subprocess.Popen(["ffmpeg", "-nostdin", "-y", "-f", "x11grab", "-framerate", "15", "-video_size", "1280x720", "-i", ":99", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(video)], env=recorder_env, stdout=log, stderr=log)
        processes.append(capture)
        time.sleep(2)
        if capture.poll() is not None or terminal.poll() is not None:
            raise RuntimeError("Screen capture or terminal failed to start")
        (output / "capture-started").touch()
        terminal.wait(timeout=600)
        capture.send_signal(signal.SIGINT)
        capture.wait(timeout=20)
        if capture.returncode not in (0, 255):
            raise RuntimeError("Screen recorder failed")
        result = json.loads((output / "session-result.json").read_text())
        probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration:stream=codec_name,width,height", "-of", "json", str(video)], capture_output=True, text=True, check=True)
        media = json.loads(probe.stdout)
        if float(media["format"]["duration"]) < 5 or not media["streams"]:
            raise ValueError("Recording has no usable video")
        result.update({"capture": "actual xterm pixels recorded by FFmpeg x11grab during execution", "mode": mode, "started_unix": started, "media": media, "video_sha256": hashlib.sha256(video.read_bytes()).hexdigest(), "cloud_demo_passed": mode == "cloud" and result["exit_code"] == 0})
        (output / "recording.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))
        return result["exit_code"]
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def scan(output: Path):
    key = os.environ.get("MOORCHEH_API_KEY", "").encode()
    for path in output.rglob("*"):
        if path.is_symlink():
            raise ValueError("Refusing linked recording evidence")
        if path.is_file() and key and key in path.read_bytes():
            raise ValueError("Refusing evidence containing the service credential")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("preflight", "session", "record", "scan"))
    parser.add_argument("--entry", type=Path, default=Path("examples/migrations/voller-attention-tiles"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("local", "cloud"), default="local")
    args = parser.parse_args()
    output, entry = args.output.resolve(), args.entry.resolve()
    screen = ScreenText(sys.stdout, os.environ.get("MOORCHEH_API_KEY", ""))
    code = 1
    with contextlib.redirect_stdout(screen), contextlib.redirect_stderr(screen):
        try:
            if args.action == "preflight":
                code = preflight(output)
            elif args.action == "session":
                code = session(entry, output, args.mode)
            elif args.action == "record":
                code = record(entry, output, args.mode)
            else:
                scan(output)
                code = 0
        except Exception as exc:
            print(f"STOPPED: {type(exc).__name__}: {exc}")
        finally:
            if args.action == "session":
                (output / "session-result.json").write_text(json.dumps({"exit_code": code}))
                time.sleep(2)
            screen.finish()
    return code


if __name__ == "__main__":
    raise SystemExit(main())

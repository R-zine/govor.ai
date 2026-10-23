from __future__ import annotations

import argparse
import asyncio
import json
import os
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from pathlib import Path

from govor_gateway_security import PairingAuthority

from .models import artifact_path, install_artifact, load_manifest, verify_artifact
from .processes import WindowsKillOnCloseJob
from .security import ensure_tls_identity

_CONTROL_PORT = 8765
_MEDIA_PORT = 8766
_LLAMA_PORT = 8767


def main(arguments: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="govor.ai")
    parser.add_argument(
        "--install-root",
        type=Path,
        default=Path(os.environ.get("GOVOR_INSTALL_ROOT", Path.cwd())),
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("doctor")
    subparsers.add_parser("model-status")
    subparsers.add_parser("install-models")
    lesson_import = subparsers.add_parser("import-lessons")
    lesson_import.add_argument("--source", type=Path, required=True)
    lesson_creator = subparsers.add_parser("create-lesson")
    lesson_creator.add_argument("--topic", required=True)
    lesson_creator.add_argument(
        "--difficulty",
        choices=("beginner", "intermediate", "advanced"),
    )
    lesson_creator.add_argument(
        "--environment",
        choices=("cafe", "supermarket", "airport", "home"),
    )
    lesson_creator.add_argument("--exercise-count", type=int)
    start = subparsers.add_parser("start")
    start.add_argument("--smoke-seconds", type=float)
    options = parser.parse_args(arguments)

    install_root = options.install_root.resolve()
    paths = ReleasePaths.from_roots(install_root, _data_root())
    if options.command == "doctor":
        _doctor(paths, require_models=False)
        print("Package prerequisites: ready")
        return 0
    if options.command == "model-status":
        return _print_model_status(paths)
    if options.command == "install-models":
        return _install_models(paths)
    if options.command == "import-lessons":
        return _import_lessons(paths, options.source)
    if options.command == "create-lesson":
        return _create_lesson(
            paths,
            topic=options.topic,
            difficulty=options.difficulty,
            environment=options.environment,
            exercise_count=options.exercise_count,
        )
    if options.command == "start":
        return _start(paths, smoke_seconds=options.smoke_seconds)
    raise AssertionError("unreachable command")


class ReleasePaths:
    def __init__(self, install_root: Path, data_root: Path) -> None:
        self.install_root = install_root
        self.data_root = data_root
        self.model_root = Path(os.environ.get("GOVOR_MODEL_ROOT", data_root / "models"))
        self.manifest = install_root / "config" / "release-models.json"
        self.python = install_root / "runtime" / "python" / "python.exe"
        self.llama = install_root / "runtime" / "llama.cpp" / "llama-server.exe"
        self.whisper = install_root / "runtime" / "whisper.cpp" / "Release" / "whisper-cli.exe"
        self.renderer = install_root / "renderer" / "GovorRenderer.exe"
        self.lessons = install_root / "content" / "lessons"
        self.credentials = data_root / "security" / "gateway-credentials.json"
        self.progress = data_root / "progress" / "progress.sqlite3"
        self.logs = data_root / "logs"

    @classmethod
    def from_roots(cls, install_root: Path, data_root: Path) -> ReleasePaths:
        return cls(install_root, data_root)


def _data_root() -> Path:
    explicit = os.environ.get("GOVOR_DATA_ROOT")
    if explicit:
        return Path(explicit).resolve()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        raise RuntimeError("LOCALAPPDATA is unavailable")
    return Path(local_app_data) / "govor.ai"


def _doctor(paths: ReleasePaths, *, require_models: bool) -> None:
    if os.name != "nt" or not sys.maxsize > 2**32:
        raise RuntimeError("govor.ai requires 64-bit Windows")
    required = [paths.python, paths.llama, paths.whisper, paths.renderer, paths.manifest]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise RuntimeError("package is incomplete: " + ", ".join(missing))
    if not paths.lessons.is_dir() or not any(paths.lessons.glob("*.json")):
        raise RuntimeError("package contains no guided lesson definitions")
    if require_models:
        unavailable = [
            artifact.display_name
            for artifact in load_manifest(paths.manifest)
            if verify_artifact(artifact_path(paths.model_root, artifact), artifact) != "ready"
        ]
        if unavailable:
            raise RuntimeError(
                "required models are missing or invalid; run Setup-Govor.cmd first: "
                + ", ".join(unavailable)
            )
    for port in (_CONTROL_PORT, _MEDIA_PORT, _LLAMA_PORT):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                raise RuntimeError(f"TCP port {port} is already in use")


def _print_model_status(paths: ReleasePaths) -> int:
    ready = True
    for artifact in load_manifest(paths.manifest):
        status = verify_artifact(artifact_path(paths.model_root, artifact), artifact)
        print(f"{artifact.display_name}: {status}")
        ready = ready and status == "ready"
    return 0 if ready else 2


def _install_models(paths: ReleasePaths) -> int:
    print(f"Models will be stored in {paths.model_root}")
    for artifact in load_manifest(paths.manifest):
        destination = artifact_path(paths.model_root, artifact)
        status = verify_artifact(destination, artifact)
        if status == "ready":
            print(f"Ready: {artifact.display_name}")
            continue
        print(f"Downloading {artifact.display_name} ({artifact.size} bytes)...")
        install_artifact(paths.model_root, artifact)
        print(f"Verified SHA-256: {artifact.sha256}")
    print("All required models passed integrity verification.")
    return 0


def _import_lessons(paths: ReleasePaths, source: Path) -> int:
    from govor_domain import import_lesson_bundle
    from govor_scene_planner import ScenePlanner

    try:
        imported = import_lesson_bundle(
            source,
            paths.lessons,
            allowed_scene_templates=set(ScenePlanner().supported_templates),
        )
    except (OSError, ValueError) as error:
        print(f"Lesson import failed: {error}", file=sys.stderr)
        return 2
    for lesson in imported:
        print(f"Imported: {lesson.title} ({lesson.scenario_id})")
    print("Lesson import completed. Running clients will receive the updated catalog.")
    return 0


def _create_lesson(
    paths: ReleasePaths,
    *,
    topic: str,
    difficulty: str | None,
    environment: str | None,
    exercise_count: int | None,
) -> int:
    from govor_domain import Difficulty
    from govor_local_ai.lesson_creator import (
        LessonCreationRequest,
        LlamaCppLessonContentProvider,
        create_lesson,
    )
    from govor_provider_interfaces import ProviderError
    from govor_scene_planner import ScenePlanner

    try:
        request = LessonCreationRequest(
            topic=topic,
            difficulty=Difficulty(difficulty) if difficulty is not None else None,
            scene_template_id=environment,
            exercise_count=exercise_count,
        )
        created = asyncio.run(
            create_lesson(
                request,
                LlamaCppLessonContentProvider(f"http://127.0.0.1:{_LLAMA_PORT}"),
                paths.lessons,
                allowed_scene_templates=set(ScenePlanner().supported_templates),
            )
        )
    except (OSError, ProviderError, TimeoutError, ValueError) as error:
        print(f"Lesson creation failed: {error}", file=sys.stderr)
        return 2
    print(f"Created: {created.imported.title} ({created.imported.scenario_id})")
    print(
        "Settings: "
        f"{created.options.difficulty.value}, {created.options.scene_template_id}, "
        f"{created.options.exercise_count} exercises"
    )
    print("The lesson is installed. Running clients will receive the updated catalog.")
    return 0


def _start(paths: ReleasePaths, *, smoke_seconds: float | None) -> int:
    _doctor(paths, require_models=True)
    paths.logs.mkdir(parents=True, exist_ok=True)
    paths.progress.parent.mkdir(parents=True, exist_ok=True)
    identity = ensure_tls_identity(paths.data_root / "security")
    pairing_code, expires_at = PairingAuthority(paths.credentials).create_pairing_code()
    lan_addresses = _lan_addresses()
    print("govor.ai is starting in local-only mode.")
    print(f"PC address: {lan_addresses[0] if lan_addresses else 'not found'}")
    print(f"Control port: {_CONTROL_PORT}   Media port: {_MEDIA_PORT}")
    print(f"Certificate SHA-256: {identity.fingerprint_sha256}")
    print(f"One-time pairing code: {pairing_code} (expires at Unix time {expires_at})")
    print("The phone must be on the same trusted Wi-Fi network.")

    environment = _release_environment(paths, identity.certificate)
    children: list[subprocess.Popen[bytes]] = []
    logs: list[object] = []
    with WindowsKillOnCloseJob() as job:
        try:
            children.append(
                _spawn(
                    [
                        str(paths.llama),
                        "-m",
                        str(paths.model_root / "qwen" / "Qwen3-4B-Q4_K_M.gguf"),
                        "--host",
                        "127.0.0.1",
                        "--port",
                        str(_LLAMA_PORT),
                        "-ngl",
                        "99",
                        "-c",
                        "4096",
                        "--jinja",
                        "--no-webui",
                        "--log-disable",
                    ],
                    paths.logs / "llama.log",
                    environment,
                    job,
                    logs,
                )
            )
            _wait_health(
                f"http://127.0.0.1:{_LLAMA_PORT}/health",
                None,
                children,
                timeout_seconds=180,
            )
            children.append(
                _spawn(
                    _uvicorn_command(
                        paths,
                        "govor_media.entrypoint:app",
                        _MEDIA_PORT,
                        identity.certificate,
                        identity.private_key,
                    ),
                    paths.logs / "media.log",
                    environment,
                    job,
                    logs,
                )
            )
            _wait_health(
                f"https://localhost:{_MEDIA_PORT}/health",
                identity.certificate,
                children,
            )
            children.append(
                _spawn(
                    _uvicorn_command(
                        paths,
                        "govor_host.app:app",
                        _CONTROL_PORT,
                        identity.certificate,
                        identity.private_key,
                    ),
                    paths.logs / "host.log",
                    environment,
                    job,
                    logs,
                )
            )
            _wait_health(
                f"https://localhost:{_CONTROL_PORT}/health",
                identity.certificate,
                children,
            )
            renderer = subprocess.Popen(  # noqa: S603 - executable is package-owned
                _renderer_command(paths, identity.certificate),
                cwd=paths.install_root / "renderer",
                env=environment,
            )
            job.add(renderer)
            children.append(renderer)
            if smoke_seconds is None:
                input("Services are ready. Press Enter to stop govor.ai.\n")
            else:
                if smoke_seconds <= 0 or smoke_seconds > 300:
                    raise ValueError("smoke duration must be between 0 and 300 seconds")
                time.sleep(smoke_seconds)
            return 0
        except KeyboardInterrupt:
            return 130
        finally:
            _stop_children(children)
            for stream in logs:
                stream.close()  # type: ignore[attr-defined]
            print("govor.ai stopped; managed child processes were closed.")


def _renderer_command(paths: ReleasePaths, certificate: Path) -> list[str]:
    command = [str(paths.renderer), "--", "--mute-local-audio"]
    fixture_delay = os.environ.get("GOVOR_RENDERER_FIXTURE_TONE_DELAY_SECONDS")
    if fixture_delay is None:
        command.append("--no-startup-tone")
    else:
        try:
            delay_seconds = float(fixture_delay)
        except ValueError as error:
            raise RuntimeError("the renderer fixture tone delay must be numeric") from error
        if not 0.0 <= delay_seconds <= 300.0:
            raise RuntimeError("the renderer fixture tone delay must be between 0 and 300 seconds")
        command.append(f"--startup-tone-delay-seconds={delay_seconds:g}")
    command.extend(
        [
            f"--control-url=wss://localhost:{_CONTROL_PORT}/v1/renderer/control",
            f"--control-ca={certificate}",
        ]
    )
    return command


def _release_environment(paths: ReleasePaths, certificate: Path) -> dict[str, str]:
    environment = os.environ.copy()
    source_roots = [
        paths.install_root / "app" / relative
        for relative in (
            "apps/launcher/src",
            "apps/host/src",
            "packages/domain/src",
            "packages/gateway_security/src",
            "packages/provider_interfaces/src",
            "packages/progress/src",
            "packages/scene_planner/src",
            "packages/contracts/python",
            "services/local_ai/src",
            "services/provider_router/src",
            "services/speech/src",
            "services/media/src",
        )
    ]
    environment.update(
        {
            "GOVOR_INSTALL_ROOT": str(paths.install_root),
            "PYTHONPATH": os.pathsep.join(str(path) for path in source_roots),
            "GOVOR_MODE": "local",
            "GOVOR_BIND_HOST": "0.0.0.0",  # noqa: S104 - authenticated WSS gateway
            "GOVOR_PORT": str(_CONTROL_PORT),
            "GOVOR_SECURE_GATEWAY": "true",
            "GOVOR_GATEWAY_CREDENTIALS_FILE": str(paths.credentials),
            "GOVOR_WHISPER_EXECUTABLE": str(paths.whisper),
            "GOVOR_WHISPER_MODEL": str(paths.model_root / "whisper" / "ggml-small.bin"),
            "GOVOR_LLAMA_BASE_URL": f"http://127.0.0.1:{_LLAMA_PORT}",
            "GOVOR_DIALOGUE_PROVIDER_ID": "llama.cpp-qwen3-4b-q4_k_m",
            "GOVOR_KOKORO_MODEL": str(paths.model_root / "speech" / "kokoro-v1.0.onnx"),
            "GOVOR_KOKORO_VOICES": str(paths.model_root / "speech" / "voices-v1.0.bin"),
            "GOVOR_PIPER_BG_MODEL": str(paths.model_root / "speech" / "bg_BG-dimitar-medium.onnx"),
            "GOVOR_PIPER_BG_CONFIG": str(
                paths.model_root / "speech" / "bg_BG-dimitar-medium.onnx.json"
            ),
            "GOVOR_MEDIA_CAPTURE_URL": f"https://localhost:{_MEDIA_PORT}",
            "GOVOR_MEDIA_CAPTURE_TLS_CA": str(certificate),
            "GOVOR_MEDIA_SOURCE": "renderer",
            "GOVOR_PROGRESS_DATABASE": str(paths.progress),
            "GOVOR_LESSON_DIRECTORY": str(paths.lessons),
            "GOVOR_OFFLINE_ONLY": "true",
        }
    )
    environment.pop("GOVOR_DEV_PAIRING_TOKEN", None)
    return environment


def _uvicorn_command(
    paths: ReleasePaths,
    application: str,
    port: int,
    certificate: Path,
    private_key: Path,
) -> list[str]:
    return [
        str(paths.python),
        "-m",
        "uvicorn",
        application,
        "--host",
        "0.0.0.0",  # noqa: S104 - authenticated WSS gateway
        "--port",
        str(port),
        "--ssl-certfile",
        str(certificate),
        "--ssl-keyfile",
        str(private_key),
        "--no-access-log",
    ]


def _spawn(
    command: list[str],
    log_path: Path,
    environment: dict[str, str],
    job: WindowsKillOnCloseJob,
    logs: list[object],
) -> subprocess.Popen[bytes]:
    stream = log_path.open("ab", buffering=0)
    logs.append(stream)
    creation_flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = subprocess.Popen(  # noqa: S603 - commands are package-owned constants
        command,
        cwd=environment["GOVOR_INSTALL_ROOT"],
        env=environment,
        stdout=stream,
        stderr=subprocess.STDOUT,
        creationflags=creation_flags,
    )
    job.add(process)
    return process


def _wait_health(
    uri: str,
    certificate: Path | None,
    children: list[subprocess.Popen[bytes]],
    *,
    timeout_seconds: float = 60,
) -> None:
    context = (
        ssl.create_default_context(cafile=str(certificate)) if certificate is not None else None
    )
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        for process in children:
            if process.poll() is not None:
                raise RuntimeError(f"a managed service exited with code {process.returncode}")
        try:
            with urllib.request.urlopen(  # noqa: S310 - fixed localhost HTTPS health URL
                uri, timeout=1, context=context
            ) as response:
                status = json.loads(response.read(64 * 1024))["status"]
                if status == "ok":
                    return
        except (OSError, KeyError, ValueError, urllib.error.URLError):
            time.sleep(0.25)
    raise RuntimeError(f"service did not become healthy: {uri}")


def _stop_children(children: list[subprocess.Popen[bytes]]) -> None:
    for process in reversed(children):
        if process.poll() is None:
            process.terminate()
    deadline = time.monotonic() + 5
    for process in reversed(children):
        remaining = max(0.0, deadline - time.monotonic())
        try:
            process.wait(timeout=remaining)
        except subprocess.TimeoutExpired:
            process.kill()
    for process in children:
        if process.poll() is None:
            process.wait(timeout=5)


def _lan_addresses() -> list[str]:
    addresses: set[str] = set()
    try:
        for family, _, _, _, socket_address in socket.getaddrinfo(socket.gethostname(), None):
            if family != socket.AF_INET:
                continue
            address = socket_address[0]
            if not isinstance(address, str):
                continue
            if not address.startswith("127.") and not address.startswith("169.254."):
                addresses.add(address)
    except socket.gaierror:
        pass
    return sorted(addresses)


if __name__ == "__main__":
    raise SystemExit(main())

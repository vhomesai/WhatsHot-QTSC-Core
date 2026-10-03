from pathlib import Path
import os
import re
import subprocess
import sys
import tomllib

import yaml

from scripts.validate_runtime_lock import SUPPORTED_PYTHONS, resolution_command


ROOT = Path(__file__).resolve().parents[1]


def _read(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_compose_is_hardened_and_api_is_internal(monkeypatch):
    monkeypatch.setenv("TRIQEE_ADMIN_KEY", "validator-only-placeholder")
    compose = yaml.safe_load(_read("docker-compose.yml"))
    api = compose["services"]["api"]
    caddy = compose["services"]["caddy"]

    assert "ports" not in api
    assert api["read_only"] is True
    assert api["restart"] == "unless-stopped"
    assert api["cap_drop"] == ["ALL"]
    assert "no-new-privileges:true" in api["security_opt"]
    assert api["environment"]["TRIQEE_CORS_ORIGINS"] == "https://www.triqee.com"
    assert api["environment"]["TRIQEE_DB_PATH"] == "/app/data/operational.db"
    assert "/app/data" in api["volumes"][0]
    assert compose["networks"]["backend"]["internal"] is True

    assert caddy["user"] == "1000:1000"
    assert caddy["read_only"] is True
    assert caddy["cap_drop"] == ["ALL"]
    assert caddy["cap_add"] == ["NET_BIND_SERVICE"]
    assert set(caddy["ports"]) == {"80:80", "443:443", "443:443/udp"}
    assert caddy["networks"] == ["edge", "backend"]
    assert caddy["environment"]["TRIQEE_SITE_ADDRESS"].endswith("www.triqee.com}")


def test_dockerfile_installs_project_and_runs_expected_app_as_non_root():
    dockerfile = _read("Dockerfile")
    assert dockerfile.startswith("# syntax=docker/dockerfile:1.7\nFROM python:3.12.15-slim-bookworm")
    assert "pip install --no-cache-dir -r requirements.lock" in dockerfile
    assert "pip install --no-cache-dir --no-deps ." in dockerfile
    assert "TRIQEE_DB_PATH=/app/data/operational.db" in dockerfile
    assert "python -m compileall -q src" in dockerfile
    assert "find_spec('src.api_server')" in dockerfile
    assert "from src.api_server import" not in dockerfile
    assert "gemini_agent_dashboard.db" not in dockerfile
    assert "requirements.txt" not in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert '"src.api_server:app"' in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "apt-get" not in dockerfile


def test_runtime_import_initializes_configured_database_only(tmp_path):
    runtime_database = tmp_path / "data" / "operational.db"
    environment = os.environ.copy()
    environment["TRIQEE_DB_PATH"] = str(runtime_database)
    subprocess.run(
        [
            sys.executable,
            "-c",
            "from src.api_server import DB_PATH, app; "
            "assert DB_PATH == __import__('os').environ['TRIQEE_DB_PATH']; "
            "assert app.title",
        ],
        cwd=ROOT,
        env=environment,
        check=True,
        capture_output=True,
        text=True,
    )
    assert runtime_database.is_file()
    assert not (tmp_path / "gemini_agent_dashboard.db").exists()


def test_runtime_lock_covers_project_dependencies_and_email_validation_extra():
    project = tomllib.loads(_read("pyproject.toml"))
    project_dependencies = project["project"]["dependencies"]
    lock_lines = [
        line
        for line in _read("requirements.lock").splitlines()
        if line and not line.startswith("#")
    ]

    def normalized_name(requirement: str) -> str:
        base = re.split(r"[<>=!~\[]", requirement, maxsplit=1)[0]
        return base.lower().replace("_", "-")

    direct_names = {normalized_name(requirement) for requirement in project_dependencies}
    locked_names = {normalized_name(requirement) for requirement in lock_lines}
    assert direct_names <= locked_names
    assert "pydantic[email]==2.12.5" in project_dependencies
    assert "email-validator" in locked_names
    assert "greenlet==3.5.6" in lock_lines
    assert "pydantic==2.12.5" in lock_lines
    assert "pydantic-core==2.41.5" in lock_lines
    assert "typing-inspection==0.4.2" in lock_lines
    assert all("==" in requirement for requirement in project_dependencies)
    assert all("==" in requirement for requirement in lock_lines)


def test_runtime_lock_resolution_commands_cover_declared_ci_matrix():
    workflow = _read(".github/workflows/ci.yml")
    project = tomllib.loads(_read("pyproject.toml"))

    assert SUPPORTED_PYTHONS == ("3.12", "3.13", "3.14")
    assert 'python-version: ["3.12", "3.13", "3.14"]' in workflow
    assert project["project"]["requires-python"] == ">=3.12"
    for version in SUPPORTED_PYTHONS:
        command = resolution_command(version)
        assert "--dry-run" in command
        assert "--only-binary=:all:" in command
        assert "manylinux_2_28_x86_64" in command
        assert "manylinux_2_17_x86_64" in command
        assert f"cp{version.replace('.', '')}" in command
        assert str(ROOT / "requirements.lock") in command


def test_caddy_static_structure_is_non_authoritative_but_security_complete():
    caddyfile = _read("Caddyfile")
    assert "{$TRIQEE_SITE_ADDRESS:www.triqee.com} {" in caddyfile
    assert "@cockpit path /cockpit /cockpit/" in caddyfile
    assert "rewrite * /triqee_si_chatbot.html" in caddyfile
    assert "handle /api/health" in caddyfile
    assert "rewrite * /health" in caddyfile
    assert "@api path /api/*" in caddyfile
    assert "reverse_proxy api:8000" in caddyfile
    assert "flush_interval -1" in caddyfile
    assert "max_size 10MB" in caddyfile
    assert "encode zstd gzip" in caddyfile
    assert "Strict-Transport-Security" in caddyfile
    assert "Content-Security-Policy" in caddyfile
    assert caddyfile.count("{") == caddyfile.count("}")


def test_render_and_workflow_yaml_parse_structurally():
    render = yaml.safe_load(_read("render.yaml"))
    service = render["services"][0]
    assert "requirements.lock" in service["buildCommand"]
    assert "pip install --no-deps ." in service["buildCommand"]
    assert "python -m compileall -q src" in service["buildCommand"]
    assert "find_spec('src.api_server')" in service["buildCommand"]
    assert "from src.api_server import" not in service["buildCommand"]
    assert service["startCommand"].startswith("uvicorn src.api_server:app")
    assert service["healthCheckPath"] == "/health"
    assert service["disk"]["mountPath"] == "/opt/render/project/data"

    for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
        parsed = yaml.safe_load(workflow.read_text(encoding="utf-8"))
        assert isinstance(parsed, dict), workflow


def test_tracked_deployment_references_only_existing_manifests():
    candidates = [
        ROOT / "Dockerfile",
        ROOT / "docker-compose.yml",
        ROOT / "render.yaml",
        ROOT / "README.md",
        *(ROOT / ".github" / "workflows").glob("*.yml"),
    ]
    referenced = set()
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        referenced.update(
            match.group(1)
            for match in re.finditer(r"(?:pip|python -m pip) install -r\s+([^\s&`]+)", text)
        )
    assert referenced
    assert all((ROOT / manifest).is_file() for manifest in referenced)
    assert "requirements.txt" not in referenced


def test_build_context_excludes_secrets_databases_and_generated_state():
    ignored = set(_read(".dockerignore").splitlines())
    for required in {
        ".env",
        ".env.*",
        ".git",
        "*.db",
        "*.db-wal",
        "*.sqlite",
        "*.pem",
        "*.key",
        "*.zip",
        "*.tar.gz",
        "tests",
        "benchmarks",
    }:
        assert required in ignored

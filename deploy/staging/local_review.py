"""Explicit local-only operations. Preparation/check never starts a service."""
import argparse
from datetime import datetime, timedelta, UTC
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import subprocess

REPO = Path(__file__).resolve().parents[2]
COMPOSE = REPO / "deploy/staging/compose.yaml"
PROJECT = "ai-effect-review-staging-20261101"
DOCKER = ["docker", "--context", "desktop-linux"]


def command(arguments, **kwargs):
    if arguments[:len(DOCKER)] == DOCKER:
        kwargs.setdefault("env", {key: value for key, value in os.environ.items() if not key.startswith("STAGING_")})
    return subprocess.run(arguments, check=True, **kwargs)


def private_write(path, content):
    with path.open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(content)


def password():
    while True:
        value = secrets.token_urlsafe(32)
        if re.search("[A-Z]", value) and re.search("[a-z]", value) and re.search("[0-9]", value):
            return value


def prepare(directory, build_record):
    if directory.exists():
        raise RuntimeError("Choose a new private directory; preparation never replaces credentials")
    record = json.loads(build_record.read_text())
    endpoint = subprocess.check_output(["docker", "context", "inspect", "desktop-linux", "--format", '{{(index .Endpoints "docker").Host}}'], text=True).strip()
    if not endpoint.startswith("npipe:") or "dockerDesktopLinuxEngine" not in endpoint:
        raise RuntimeError("This proposal requires the local Windows Docker Desktop Linux engine")
    projects = json.loads(subprocess.check_output(DOCKER + ["compose", "ls", "--format", "json"], text=True))
    if any(project["Name"] == PROJECT for project in projects):
        raise RuntimeError("The proposed project already exists; preserve it")
    directory.mkdir(parents=True)
    if os.name == "nt":
        user = subprocess.check_output(["whoami"], text=True).strip()
        command(["icacls", str(directory), "/inheritance:r", "/grant:r", user + ":(OI)(CI)F", "*S-1-5-18:(OI)(CI)F"], stdout=subprocess.DEVNULL)
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "AI-EFFECT local review localhost")])
    now = datetime.now(UTC)
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=30))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .add_extension(x509.ExtendedKeyUsage([x509.oid.ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(key, hashes.SHA256()))
    tls = directory / "tls"; tls.mkdir()
    (tls / "localhost.key").write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    (tls / "localhost.crt").write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    credentials = {"administrator": {"email": "review-admin@staging.invalid", "password": password()},
                   "designer_a": {"email": "reviewer-a@staging.invalid", "password": password()},
                   "designer_b": {"email": "reviewer-b@staging.invalid", "password": password()}}
    images = {image["role"]: image["image_id"] for image in record["images"]}
    required = {"api", "web", "postgres", "gateway"}
    if set(images) != required or any(not re.fullmatch(r"sha256:[a-f0-9]{64}", value) for value in images.values()):
        raise RuntimeError("The build record must name four exact local image identities")
    settings = {"STAGING_PROJECT_NAME": PROJECT, "STAGING_GATEWAY_PORT": "24443", "STAGING_DATABASE_NAME": "design_ai_staging",
        "STAGING_TLS_DIR": tls.as_posix(), "STAGING_POSTGRES_PASSWORD": password(),
        **{"STAGING_" + role.upper() + "_IMAGE": image for role, image in images.items()}}
    bootstrap = dict(settings, STAGING_BOOTSTRAP_EMAIL=credentials["administrator"]["email"], STAGING_BOOTSTRAP_PASSWORD=credentials["administrator"]["password"])
    for label in ("a", "b"):
        bootstrap["STAGING_DESIGNER_" + label.upper() + "_EMAIL"] = credentials["designer_" + label]["email"]
        bootstrap["STAGING_DESIGNER_" + label.upper() + "_PASSWORD"] = credentials["designer_" + label]["password"]
    runtime = dict(bootstrap)
    for key_name in runtime:
        if key_name.startswith("STAGING_BOOTSTRAP_") or key_name.startswith("STAGING_DESIGNER_"):
            runtime[key_name] = ""
    for filename, values in [("bootstrap.env", bootstrap), ("runtime.env", runtime)]:
        private_write(directory / filename, "".join(key_name + "=" + value + "\n" for key_name, value in values.items()))
    private_write(directory / "credentials.json", json.dumps(credentials, indent=2))
    private_write(directory / "proposal.json", json.dumps({"project": PROJECT, "browser_url": "https://127.0.0.1:24443",
        "certificate_thumbprint": certificate.fingerprint(hashes.SHA1()).hex().upper(), "images": images,
        "source_commit": record["source_commit"], "services_started": False, "accounts_created": False}, indent=2))
    print(json.dumps({"private_directory": str(directory), "prepared_only": True, "services_started": False, "accounts_created": False}))


def operate(directory, action, approved, backup=None, restore_name=None):
    proposal = json.loads((directory / "proposal.json").read_text())
    if proposal["project"] != PROJECT:
        raise RuntimeError("Not this isolated review proposal")
    if action not in {"check", "verify"} and not approved:
        raise RuntimeError("This action requires explicit --approve-provisioning after owner approval")
    environment_file = directory / ("bootstrap.env" if action == "bootstrap" else "runtime.env")
    values = dict(line.split("=", 1) for line in environment_file.read_text().splitlines() if "=" in line)
    if (values.get("STAGING_PROJECT_NAME") != PROJECT or values.get("STAGING_GATEWAY_PORT") != "24443"
            or Path(values.get("STAGING_TLS_DIR", "")).resolve() != (directory / "tls").resolve()
            or not re.fullmatch(r"design_ai_staging(?:_restore_[0-9]{14})?", values.get("STAGING_DATABASE_NAME", ""))):
        raise RuntimeError("The local proposal identity, loopback port, TLS directory or database differs")
    compose = DOCKER + ["compose", "--project-name", PROJECT, "--env-file", str(environment_file), "-f", str(COMPOSE)]
    for image in proposal["images"].values():
        found = json.loads(subprocess.check_output(DOCKER + ["image", "inspect", image], text=True))[0]
        if found["Id"] != image:
            raise RuntimeError("A pinned local candidate image is unavailable")
    command(compose + ["config", "--quiet"])
    if action == "check":
        print(json.dumps({"config": "valid", "pinned_images": 4, "services_started_by_check": False, "browser_url": proposal["browser_url"]}))
    elif action == "migrate":
        command(compose + ["up", "-d", "--wait", "--pull", "never", "postgres"])
        # 001 adds authentication to an existing portal schema. A fresh volume
        # first needs its four core tables, without importing main/startup or
        # precreating users (which would omit 001's database constraints).
        initialize = ("from app.db import Base,engine; "
            "from app.models.service import Service; from app.models.solution import Solution; "
            "from app.models.deployment import Deployment; from app.models.operation_contract import OperationContract; "
            "assert engine.url.database=='design_ai_staging' and engine.url.host=='postgres'; "
            "Base.metadata.create_all(engine,tables=[Service.__table__,Solution.__table__,Deployment.__table__,OperationContract.__table__])")
        command(compose + ["run", "--rm", "--no-deps", "--pull", "never", "api", "python", "-c", initialize])
        for migration in sorted((REPO / "deploy/migrations").glob("*.sql")):
            command(compose + ["exec", "-T", "postgres", "psql", "-U", "staging", "-d", "design_ai_staging", "-v", "ON_ERROR_STOP=1"], input=migration.read_bytes())
    elif action == "bootstrap":
        command(compose + ["run", "--rm", "--no-deps", "--pull", "never", "api", "python", "/opt/staging/synthetic_seed.py"])
    elif action == "start":
        command(compose + ["up", "-d", "--no-build", "--pull", "never", "postgres", "api", "web", "gateway"])
    elif action == "stop":
        command(compose + ["stop", "gateway", "web", "api", "postgres"])
    elif action == "backup":
        destination = directory / ("staging-" + datetime.now(UTC).strftime("%Y%m%d%H%M%S") + ".dump")
        with destination.open("xb") as stream:
            command(compose + ["exec", "-T", "postgres", "pg_dump", "-U", "staging", "-Fc", "-d", values["STAGING_DATABASE_NAME"]], stdout=stream)
        print(json.dumps({"backup": str(destination), "sha256": hashlib.sha256(destination.read_bytes()).hexdigest()}))
    elif action == "restore":
        if not backup or not backup.is_file() or not restore_name or not re.fullmatch(r"design_ai_staging_restore_[0-9]{14}", restore_name):
            raise RuntimeError("Restore requires a retained backup and a new design_ai_staging_restore_YYYYMMDDHHMMSS database")
        command(compose + ["stop", "gateway", "web", "api"])
        command(compose + ["exec", "-T", "postgres", "createdb", "-U", "staging", restore_name])
        command(compose + ["exec", "-T", "postgres", "pg_restore", "-U", "staging", "--exit-on-error", "-d", restore_name], input=backup.read_bytes())
        print(json.dumps({"restored_database": restore_name, "original_database_preserved": True,
                          "next": "Review the restored database, then explicitly set STAGING_DATABASE_NAME in runtime.env before starting"}))
    elif action == "verify":
        certificate = str(directory / "tls/localhost.crt")
        probes = [("/login", "GET", "200"), ("/api/health", "GET", "200"), ("/api/auth/me", "GET", "401"),
                  ("/api/design-ai/chat", "POST", "403"), ("/api/workflows/submit-to-orchestrator", "POST", "403"),
                  ("/api/design-ai/drafts/probe/execute", "POST", "403"), ("/api/data-references/preview", "POST", "403")]
        for path, method, expected in probes:
            result = subprocess.check_output(["curl.exe", "--silent", "--show-error", "--cacert", certificate,
                "--output", "NUL", "--write-out", "%{http_code}", "--request", method, proposal["browser_url"] + path], text=True).strip()
            if result != expected:
                raise RuntimeError("Verification failed for " + path + ": " + result)
        print(json.dumps({"HTTPS": "verified with explicit local certificate", "probes": len(probes), "provider_or_workflow_attempts": 0}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["prepare", "check", "migrate", "bootstrap", "start", "verify", "backup", "restore", "stop"])
    parser.add_argument("--private-dir", type=Path, required=True)
    parser.add_argument("--build-record", type=Path)
    parser.add_argument("--approve-provisioning", action="store_true")
    parser.add_argument("--backup", type=Path)
    parser.add_argument("--restore-name")
    args = parser.parse_args()
    if args.action == "prepare":
        if not args.build_record:
            parser.error("prepare requires --build-record")
        prepare(args.private_dir.resolve(), args.build_record)
    else:
        operate(args.private_dir.resolve(), args.action, args.approve_provisioning, args.backup, args.restore_name)

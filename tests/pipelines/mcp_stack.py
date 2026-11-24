"""One local incidents API, OIDC issuer, and company-tools MCP server.

The support-agent tests talk to this stack through langchain-mcp-adapters.
The staff token is given only to the MCP process. The agent receives a
separate OAuth access token.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import jwt
import uvicorn
from cryptography.hazmat.primitives.asymmetric import rsa

_ROOT = Path(__file__).resolve().parents[2]
_AUDIENCE = "https://mcp.test/mcp"
_SCOPES = "incidents.read,inventory.read"


class Stack:
    def __init__(self) -> None:
        self.api_port = _free_port()
        self.mcp_port = _free_port()
        self.issuer_port = _free_port()
        self.issuer = f"http://127.0.0.1:{self.issuer_port}"
        self.mcp_url = f"http://127.0.0.1:{self.mcp_port}/mcp"
        self.access_token = ""
        self._api: uvicorn.Server | None = None
        self._issuer: ThreadingHTTPServer | None = None
        self._mcp: subprocess.Popen[str] | None = None
        self._db_path: Path | None = None
        self._previous_db: Path | None = None

    def start(self, db_path: Path) -> None:
        import app.database as database
        from app.incidents import seed_incidents
        from fastapi.testclient import TestClient

        self._db_path = db_path
        self._previous_db = database.DEFAULT_DB_PATH
        database.DEFAULT_DB_PATH = db_path
        seeded = seed_incidents(db_path)
        if seeded.total != 100:
            raise RuntimeError(f"Incident seed total was {seeded.total}")
        application = _incidents_app()
        self._application = application
        with TestClient(application) as client:
            registered = client.post(
                "/users",
                json={"email": "staff@brasaland.com", "password": "secret-pass"},
            )
            if registered.status_code not in {201, 409}:
                raise RuntimeError(registered.text)
            logged = client.post(
                "/auth/login",
                json={"email": "staff@brasaland.com", "password": "secret-pass"},
            )
            if logged.status_code != 200:
                raise RuntimeError(logged.text)
            staff_token = logged.json()["access_token"]
        self._start_api()
        signing = _signing_key()
        self._start_issuer(signing["jwks"])
        self.access_token = _agent_token_for(self.issuer, signing["key"])
        self._start_mcp(staff_token)
        os.environ["MCP_SERVER_URL"] = self.mcp_url
        os.environ["MCP_ACCESS_TOKEN"] = self.access_token

    def stop(self) -> None:
        if self._mcp is not None and self._mcp.poll() is None:
            self._mcp.terminate()
            try:
                self._mcp.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._mcp.kill()
        if self._api is not None:
            self._api.should_exit = True
        if self._issuer is not None:
            self._issuer.shutdown()
        if self._previous_db is not None:
            import app.database as database

            database.DEFAULT_DB_PATH = self._previous_db

    def _start_api(self) -> None:
        config = uvicorn.Config(
            self._application,
            host="127.0.0.1",
            port=self.api_port,
            log_level="warning",
        )
        self._api = uvicorn.Server(config)
        threading.Thread(target=self._api.run, name="incidents-api", daemon=True).start()
        _wait(f"http://127.0.0.1:{self.api_port}/health")

    def _start_issuer(self, jwks: dict) -> None:
        issuer = self.issuer
        metadata = {
            "issuer": issuer,
            "authorization_endpoint": f"{issuer}/authorize",
            "token_endpoint": f"{issuer}/token",
            "jwks_uri": f"{issuer}/jwks",
            "response_types_supported": ["code"],
            "grant_types_supported": ["authorization_code"],
            "code_challenge_methods_supported": ["S256"],
            "subject_types_supported": ["public"],
            "id_token_signing_alg_values_supported": ["RS256"],
        }
        body = json.dumps(metadata).encode()
        keys = json.dumps(jwks).encode()

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                if self.path == "/.well-known/openid-configuration":
                    payload = body
                elif self.path == "/jwks":
                    payload = keys
                else:
                    self.send_response(404)
                    self.end_headers()
                    return
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format: str, *args: object) -> None:
                return

        self._issuer = ThreadingHTTPServer(("127.0.0.1", self.issuer_port), Handler)
        threading.Thread(
            target=self._issuer.serve_forever,
            name="oidc-issuer",
            daemon=True,
        ).start()

    def _start_mcp(self, staff_token: str) -> None:
        env = os.environ.copy()
        env.update(
            {
                "INCIDENTS_API_BASE_URL": f"http://127.0.0.1:{self.api_port}",
                "INCIDENTS_API_TIMEOUT_SECONDS": "5",
                "INCIDENTS_API_TOKEN": staff_token,
                "MCP_AUTH_ISSUER": self.issuer,
                "MCP_AUTH_AUDIENCE": _AUDIENCE,
                "MCP_AUTH_RESOURCE": _AUDIENCE,
                "MCP_AUTH_SCOPES": _SCOPES,
                "MCP_AUTH_INCIDENTS_SCOPE": "incidents.read",
                "MCP_AUTH_INVENTORY_SCOPE": "inventory.read",
                "MCP_HOST": "127.0.0.1",
                "MCP_PORT": str(self.mcp_port),
            }
        )
        env.pop("MCP_SERVER_URL", None)
        env.pop("MCP_ACCESS_TOKEN", None)
        env["PYTHONPATH"] = str(_ROOT / "mcps" / "company-tools")
        self._logs: list[str] = []
        self._mcp = subprocess.Popen(
            [
                str(_ROOT / "mcps" / "company-tools" / ".venv" / "bin" / "python"),
                "-c",
                "from company_tools.server import main; main()",
            ],
            cwd=str(_ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        def _drain() -> None:
            if self._mcp is None or self._mcp.stdout is None:
                return
            for line in self._mcp.stdout:
                self._logs.append(line)

        threading.Thread(target=_drain, name="mcp-logs", daemon=True).start()
        deadline = time.time() + 30
        while time.time() < deadline:
            if self._mcp.poll() is not None:
                raise RuntimeError(f"MCP server exited\n{''.join(self._logs)}")
            try:
                response = httpx.get(f"http://127.0.0.1:{self.mcp_port}/health", timeout=0.5)
            except httpx.HTTPError:
                time.sleep(0.2)
                continue
            if response.status_code == 200:
                return
            time.sleep(0.2)
        raise RuntimeError("MCP server did not become healthy")


def _incidents_app():
    """Incidents plus staff login. The full API app also requires REDIS_URL."""
    from fastapi import FastAPI

    from app.routers import auth, incidents, users

    application = FastAPI()
    application.include_router(users.router)
    application.include_router(auth.router)
    application.include_router(incidents.router)

    @application.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return application


def ensure_stack(db_path: Path) -> Stack:
    current = getattr(ensure_stack, "stack", None)
    if isinstance(current, Stack):
        return current
    if str(_ROOT / "services" / "api") not in sys.path:
        sys.path.insert(0, str(_ROOT / "services" / "api"))
    stack = Stack()
    stack.start(db_path)
    ensure_stack.stack = stack
    return stack


def _free_port() -> int:
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()
    return port


def _wait(url: str) -> None:
    deadline = time.time() + 20
    while time.time() < deadline:
        try:
            response = httpx.get(url, timeout=0.5)
        except httpx.HTTPError:
            time.sleep(0.1)
            continue
        if response.status_code == 200:
            return
        time.sleep(0.1)
    raise RuntimeError(f"{url} did not respond")


def _signing_key() -> dict:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key()))
    public.update({"kid": "test-key", "alg": "RS256", "use": "sig"})
    return {"key": key, "jwks": {"keys": [public]}}


def _agent_token_for(issuer: str, key: object) -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "iss": issuer,
            "aud": _AUDIENCE,
            "sub": "agent-user",
            "client_id": "agent-support",
            "scope": "incidents.read",
            "iat": now - 30,
            "exp": now + 600,
        },
        key,
        algorithm="RS256",
        headers={"kid": "test-key"},
    )

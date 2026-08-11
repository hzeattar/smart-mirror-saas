from __future__ import annotations

import asyncio
import hmac
import os
import subprocess
import threading
import time

import modal


APP_NAME = "smart-mirror-nvidia-nim"
NIM_IMAGE = "nvcr.io/nim/black-forest-labs/flux.2-klein-4b:1.0.2-variant"
NIM_CACHE_PATH = "/opt/nim/.cache"
NIM_URL = "http://127.0.0.1:8000"
MAX_BODY_BYTES = 50 * 1024 * 1024

app = modal.App(APP_NAME)
ngc_registry = modal.Secret.from_name("smart-mirror-ngc-registry")
runtime_secrets = modal.Secret.from_name("smart-mirror-nim-runtime")
nim_cache = modal.Volume.from_name("smart-mirror-nim-cache", create_if_missing=True)
runtime_state = modal.Dict.from_name("smart-mirror-nim-state", create_if_missing=True)

gateway_dependencies = ["fastapi==0.116.1", "httpx==0.28.1"]
health_image = modal.Image.debian_slim(python_version="3.12").uv_pip_install(
    *gateway_dependencies
)
nim_image = (
    modal.Image.from_registry(
        NIM_IMAGE,
        secret=ngc_registry,
        add_python="3.12",
    )
    .entrypoint([])
    .uv_pip_install(*gateway_dependencies)
)


def _authorized(request) -> bool:
    header = request.headers.get("authorization", "")
    scheme, _, provided = header.partition(" ")
    expected = os.environ.get("GATEWAY_BEARER_TOKEN", "")
    return (
        scheme.lower() == "bearer"
        and bool(provided)
        and bool(expected)
        and hmac.compare_digest(provided.strip(), expected)
    )


@app.function(
    image=health_image,
    secrets=[runtime_secrets],
    min_containers=0,
    max_containers=2,
    scaledown_window=60,
    timeout=15,
)
@modal.asgi_app()
def provider_health():
    from fastapi import FastAPI, HTTPException, Request, status

    web = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

    @web.get("/v1/health/ready")
    async def ready(request: Request):
        if not _authorized(request):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Unauthorized",
                headers={"WWW-Authenticate": "Bearer"},
            )
        last_ready_at = float(runtime_state.get("last_ready_at", 0) or 0)
        heartbeat_age = max(0, time.time() - last_ready_at) if last_ready_at else None
        if heartbeat_age is None or heartbeat_age > 90:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="NVIDIA NIM GPU is not ready",
            )
        return {"status": "ready", "provider": "modal", "heartbeat_age": heartbeat_age}

    return web


@app.cls(
    image=nim_image,
    gpu="L40S",
    cpu=8,
    memory=65536,
    secrets=[runtime_secrets],
    volumes={NIM_CACHE_PATH: nim_cache},
    min_containers=0,
    max_containers=1,
    scaledown_window=1200,
    timeout=120,
    startup_timeout=900,
)
class NimGateway:
    @modal.enter()
    def start_nim(self) -> None:
        import httpx

        os.makedirs(NIM_CACHE_PATH, exist_ok=True)
        self.nim_process = subprocess.Popen(
            ["/bin/bash", "-lc", "exec /opt/nim/start_server.sh"],
        )

        deadline = time.monotonic() + 720
        last_error = "NIM did not report readiness."
        while time.monotonic() < deadline:
            exit_code = self.nim_process.poll()
            if exit_code is not None:
                raise RuntimeError(f"NVIDIA NIM exited during startup with code {exit_code}.")
            try:
                response = httpx.get(f"{NIM_URL}/v1/health/ready", timeout=5)
                if response.is_success:
                    runtime_state["last_ready_at"] = time.time()
                    self.heartbeat_stop = threading.Event()
                    self.heartbeat_thread = threading.Thread(
                        target=self._publish_heartbeat,
                        daemon=True,
                    )
                    self.heartbeat_thread.start()
                    return
                last_error = f"NIM readiness returned HTTP {response.status_code}."
            except httpx.HTTPError as exception:
                last_error = str(exception)
            time.sleep(2)

        self.nim_process.terminate()
        raise TimeoutError(f"NVIDIA NIM startup timed out: {last_error}")

    def _publish_heartbeat(self) -> None:
        while not self.heartbeat_stop.wait(30):
            runtime_state["last_ready_at"] = time.time()

    @modal.exit()
    def stop_nim(self) -> None:
        heartbeat_stop = getattr(self, "heartbeat_stop", None)
        if heartbeat_stop is not None:
            heartbeat_stop.set()
        runtime_state["last_ready_at"] = 0
        process = getattr(self, "nim_process", None)
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                process.kill()

    @modal.asgi_app()
    def gateway(self):
        import httpx
        from fastapi import FastAPI, HTTPException, Request, status
        from fastapi.responses import Response

        web = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
        slots = asyncio.Semaphore(2)

        def require_auth(request: Request) -> None:
            if not _authorized(request):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Unauthorized",
                    headers={"WWW-Authenticate": "Bearer"},
                )

        async def proxy(method: str, path: str, body: bytes | None = None) -> Response:
            async with slots:
                timeout = httpx.Timeout(95, connect=5)
                async with httpx.AsyncClient(timeout=timeout) as client:
                    upstream = await client.request(
                        method,
                        f"{NIM_URL}{path}",
                        content=body,
                        headers={"Accept": "application/json", "Content-Type": "application/json"},
                    )
            return Response(
                content=upstream.content,
                status_code=upstream.status_code,
                media_type=upstream.headers.get("content-type", "application/json"),
                headers={"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"},
            )

        @web.get("/v1/health/ready")
        async def ready(request: Request):
            require_auth(request)
            return await proxy("GET", "/v1/health/ready")

        @web.post("/v1/images/edits")
        async def image_edit(request: Request):
            require_auth(request)
            content_length = request.headers.get("content-length")
            if content_length and int(content_length) > MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Request body too large")
            body = await request.body()
            if len(body) > MAX_BODY_BYTES:
                raise HTTPException(status_code=413, detail="Request body too large")
            return await proxy("POST", "/v1/images/edits", body)

        return web


nim_gateway = NimGateway()


@app.function(schedule=modal.Cron("30 9 * * *", timezone="Africa/Cairo"))
def open_store_warm_pool() -> None:
    nim_gateway.update_autoscaler(  # type: ignore[attr-defined]
        min_containers=1,
        scaledown_window=1200,
    )


@app.function(schedule=modal.Cron("15 22 * * *", timezone="Africa/Cairo"))
def close_store_warm_pool() -> None:
    nim_gateway.update_autoscaler(  # type: ignore[attr-defined]
        min_containers=0,
        scaledown_window=2,
    )

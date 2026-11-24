import asyncio
import os
from pathlib import Path

import httpx
import pytest

from backend.app.config import Settings
from backend.app.main import create_app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.anyio
async def test_uploaded_cam_cine_runs_private_dra_model(tmp_path):
    model, cine = os.getenv("ECHO_TEST_INFERENCE_MODEL"), os.getenv("ECHO_TEST_CINE")
    if not (model and cine):
        pytest.skip("requires a private ONNX export and an authorized CAMUS A2C test clip")

    path = Path(cine)
    app = create_app(Settings(uploads_enabled=True, upload_dir=tmp_path, inference_checkpoint=Path(model)))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver",
    ) as client:
        health = await client.get("/api/health")
        assert health.status_code == 200 and health.json()["inference_enabled"]
        upload = await client.post("/api/upload?for_inference=true", files={"file": (path.name, path.read_bytes())},
                                   data={"deidentified": "true"})
        assert upload.status_code == 201 and upload.json()["inference_status"] == "ready"
        url = f"/api/inference/{upload.json()['case_id']}"
        assert (await client.post(url, json={"view": "A2C"})).status_code == 202
        for _ in range(250):
            status = (await client.get(f"{url}/status")).json()
            if status["status"] not in {"queued", "processing"}:
                break
            await asyncio.sleep(0.2)
        assert status["status"] == "done", status
        result = (await client.get(f"{url}/result")).json()
        assert result["model"] == "DRA-UNet" and result["source"] == "uploaded"
        assert 0 < result["nonempty_masks"] <= result["frames"]
        for sheet_url in result["sheet_urls"]:
            image = await client.get(sheet_url)
            assert image.headers["cache-control"] == "private, no-store"
            assert image.content[8:12] == b"WEBP"
        assert (await client.get(f"{url}/original{path.suffix}")).status_code == 404


def test_cors_accepts_render_csv(monkeypatch):
    monkeypatch.setenv("ECHO_CORS_ORIGINS", "https://knn334.github.io, http://localhost:5173")
    assert Settings().cors_origins == ["https://knn334.github.io", "http://localhost:5173"]

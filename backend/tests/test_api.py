import base64
import json
from uuid import UUID

import httpx
import pytest

from backend.app.config import Settings
from backend.app.main import create_app

pytestmark = pytest.mark.anyio
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=")


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client(tmp_path):
    app = create_app(Settings(uploads_enabled=True, upload_max_bytes=128, upload_dir=tmp_path / "uploads"))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver",
    ) as client:
        yield client


async def test_real_reports_keep_studies_and_losses_separate(client):
    health = (await client.get("/api/health")).json()
    assert health["status"] == "ok"
    assert health["inference_enabled"] is False
    for study, split, patients, frames in (("legacy", "test", 82, 328), ("dra", "val", 50, 200)):
        overview = (await client.get("/api/overview", params={"study": study})).json()
        assert (overview["split"], overview["patients"], overview["labeled_frames"]) == (split, patients, frames)
        assert overview["disclaimer"] == "研究基线 · 非临床验证"
        metrics = (await client.get("/api/results/segmentation", params={"study": study})).json()["metrics"]
        assert metrics == overview["segmentation"]
        assert metrics[-1]["value"] is None and metrics[-1]["reason"]
    function = (await client.get("/api/results/function")).json()["metrics"]
    edv, *_others, co = function
    assert edv["mae"] == pytest.approx(8.905836529)
    assert edv["mae_ci95"] and edv["limits_of_agreement"] and edv["n_patients"] == 82 and edv["coverage"] == 1
    assert co["mae"] is None and co["bias"] is None and co["reason"]
    legacy = (await client.get("/api/results/training-history")).json()
    dra = (await client.get("/api/results/training-history?study=dra")).json()
    assert legacy["epochs"][0]["train_bce"] > 0 and legacy["epochs"][0]["train_loss"] is None
    assert dra["epochs"][0]["train_loss"] > 0 and dra["epochs"][0]["train_bce"] is None
    assert (await client.get("/docs")).status_code == 200


async def test_patient_queries_and_actual_cine(client):
    page = (await client.get("/api/patients?sort_by=EF&order=desc&page=2&page_size=4&issue_filter=missing_co")).json()
    assert (page["page"], page["total"], len(page["items"])) == (2, 82, 4)
    assert [row["EF"] for row in page["items"]] == sorted([row["EF"] for row in page["items"]], reverse=True)
    assert all(row["HR"] is None and row["CO"] is None and row["missing_reasons"]["HR"] for row in page["items"])
    search = (await client.get("/api/patients?study=dra&search=PATIENT0015")).json()
    assert search["total"] == 1 and search["split"] == "test"
    for query in ("sort_by=invalid", "page=999", "page_size=0", "issue_filter=bad"):
        response = await client.get(f"/api/patients?{query}")
        assert response.status_code == 422 and isinstance(response.json()["detail"], str)
    assert (await client.get("/api/patients/patient9999")).status_code == 404

    detail = (await client.get("/api/patients/patient0015?study=dra")).json()
    assert detail["signed_error"]["EF"] == pytest.approx(detail["patient"]["EF"] - detail["patient"]["ref_EF"])
    assert detail["error_units"]["EF"] == "百分点" and detail["units"]["EF"] == "%"
    curve, contours = detail["volume_curve"], detail["contours"]
    assert len(curve["raw"]) == 20 and curve["smoothed"] is None and curve["reason"]
    assert [(event["phase"], event["frame"]) for event in curve["events"]] == [("ED", 0), ("ES", 16)]
    assert contours["frames"]["ES"] == {"frame": 19, "prediction": None, "reference": None}
    image = await client.get(contours["atlas_url"])
    assert image.headers["content-type"] == "image/webp" and image.content[8:12] == b"WEBP"
    legacy = (await client.get("/api/patients/patient0004")).json()
    assert legacy["volume_curve"]["raw"] is None and legacy["contours"]["atlas_url"] is None


async def test_report_failures_degrade_per_study(tmp_path):
    (tmp_path / "summary.json").write_text("{}", encoding="utf-8")
    app = create_app(Settings(reports_dir=tmp_path))
    async with app.router.lifespan_context(app), httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver",
    ) as client:
        status = (await client.get("/api/health")).json()
        assert status["status"] == "degraded"
        assert status["reports"]["summary.json"] == "invalid"
        assert status["reports"]["training_history.csv"] == "missing"
        unavailable = (await client.get("/api/overview")).json()
        assert unavailable["warnings"] and unavailable["patients"] is None and unavailable["segmentation"] == []
        assert (await client.get("/api/patients")).status_code == 503
        assert (await client.get("/api/overview?study=dra")).json()["patients"] == 50
        assert (await client.post("/api/upload")).status_code == 403


async def test_upload_and_disabled_inference(client, tmp_path):
    response = await client.post("/api/upload", files={"file": ("local-name.png", PNG, "image/png")},
                                 data={"deidentified": "true"}, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 201
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    result = response.json()
    case_id = result["case_id"]
    assert UUID(case_id).version == 4 and result["inference_status"] == "disabled"
    directory = tmp_path / "uploads" / case_id
    assert (directory / "original.png").read_bytes() == PNG
    metadata = (directory / "metadata.json").read_text(encoding="utf-8")
    assert "local-name" not in metadata and json.loads(metadata)["deidentified_attestation"] is True
    url = f"/api/inference/{case_id}"
    assert (await client.post(url, json={"view": "A2C"})).status_code == 501
    assert (await client.post(url, json={"view": "other"})).status_code == 422
    assert (await client.get(f"{url}/status")).json()["status"] == "disabled"
    assert (await client.get(f"/api/upload/{case_id}/original.png")).status_code == 404


@pytest.mark.parametrize(("name", "data", "deidentified", "origin", "code"), [
    ("../evil.png", PNG, "true", None, 400),
    ("scan.svg", PNG, "true", None, 415),
    ("scan.png", b"text", "true", None, 415),
    ("scan.png", b"", "true", None, 400),
    ("scan.png", PNG * 3, "true", None, 413),
    ("scan.png", PNG, "false", None, 422),
    ("scan.png", PNG, "true", "https://unlisted.example", 403),
])
async def test_rejected_uploads_create_no_cases(client, tmp_path, name, data, deidentified, origin, code):
    response = await client.post("/api/upload", files={"file": (name, data)}, data={"deidentified": deidentified},
                                 headers={"Origin": origin} if origin else {})
    assert response.status_code == code and isinstance(response.json()["detail"], str)
    assert not (tmp_path / "uploads").exists()


async def test_streamed_upload_enforces_body_limit(client, tmp_path):
    async def body():
        yield b'--boundary\r\nContent-Disposition: form-data; name="file"; filename="scan.png"\r\n\r\n'
        yield PNG
        yield b"x" * 70000

    response = await client.post("/api/upload", content=body(), headers={"Content-Type": "multipart/form-data; boundary=boundary"})
    assert response.status_code == 413
    assert not (tmp_path / "uploads").exists()

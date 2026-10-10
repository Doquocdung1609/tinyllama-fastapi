from fastapi.testclient import TestClient
import main
from main import app
from app.config import get_settings


def test_health_and_home():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/").json()["model"] == get_settings().ollama_model


def test_pdf_upload_rejects_wrong_extension():
    response = TestClient(app).post("/documents/upload", files={"file":("notes.txt",b"not pdf","text/plain")})
    assert response.status_code == 415


def test_empty_chat_and_invalid_image_dimensions_are_rejected():
    client = TestClient(app)
    assert client.post("/chat", json={"message": ""}).status_code == 422
    response = client.post("/image/generate", json={"prompt": "test", "width": 257, "height": 512})
    assert response.status_code == 422


def test_video_rejects_non_image_file():
    response = TestClient(app).post("/video/generate", files={"file": ("notes.txt", b"x", "text/plain")},
                                    data={"num_frames": 14, "fps": 7})
    assert response.status_code == 415


def test_video_capabilities_are_explicit(monkeypatch):
    expected = {
        "status": "BLOCKED", "ready": False,
        "blockers": ["HARDWARE_VRAM", "MODEL_NOT_AVAILABLE"],
        "backend": "StableVideoDiffusionPipeline",
        "genuine_diffusion": True, "text_prompt_supported": False,
        "motion_demo_generative": False,
    }
    monkeypatch.setattr(main.video_service, "readiness", lambda: expected)

    response = TestClient(app).get("/video/capabilities")

    assert response.status_code == 200
    assert response.json() == expected


def test_video_controls_are_validated_before_inference():
    response = TestClient(app).post(
        "/video/generate",
        files={"file": ("source.webp", b"not-decoded-because-validation-runs-first", "image/webp")},
        data={"num_frames": 26, "fps": 7, "motion_bucket_id": 127},
    )
    assert response.status_code == 422


def test_chat_stream_endpoint(monkeypatch):
    monkeypatch.setattr(main, "chat_stream", lambda *args, **kwargs: iter(["Xin ", "chào!"]))
    response = TestClient(app).post("/chat/stream", json={"message": "Chào"})
    assert response.status_code == 200
    assert response.text == "Xin chào!"

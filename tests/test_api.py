from fastapi.testclient import TestClient
import main
from main import app


def test_health_and_home():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/").json()["model"] == "llama3:latest"


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


def test_chat_stream_endpoint(monkeypatch):
    monkeypatch.setattr(main, "chat_stream", lambda *args, **kwargs: iter(["Xin ", "chào!"]))
    response = TestClient(app).post("/chat/stream", json={"message": "Chào"})
    assert response.status_code == 200
    assert response.text == "Xin chào!"

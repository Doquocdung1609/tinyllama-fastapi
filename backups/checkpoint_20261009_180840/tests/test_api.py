from fastapi.testclient import TestClient
from main import app


def test_health_and_home():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    assert client.get("/").json()["model"] == "llama3:latest"


def test_pdf_upload_rejects_wrong_extension():
    response = TestClient(app).post("/documents/upload", files={"file":("notes.txt",b"not pdf","text/plain")})
    assert response.status_code == 415

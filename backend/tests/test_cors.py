from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_default_cors_allows_vite_fallback_port() -> None:
    response = client.options(
        "/api/exhibits",
        headers={
            "Origin": "http://127.0.0.1:5174",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5174"

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

BASE_URL = '/auto-download'


class TestHealthAPI:

    def test_health_returns_ok(self):
        response = client.get(f'{BASE_URL}/health')
        assert response.status_code == 200
        assert response.json() == {'ok': True}

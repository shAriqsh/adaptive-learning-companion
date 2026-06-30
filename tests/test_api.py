"""V3 + V7: API endpoints — test via FastAPI TestClient.

Uses the real app but with an in-memory SQLite database.
We override the get_db dependency to share a single connection
so all tables are visible within the same test.
"""
import os
import pytest

# Force test database before any app imports
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.setdefault("GOOGLE_API_KEY", "test-key-not-real")

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from fastapi.testclient import TestClient

from backend.app.database import Base, get_db
from backend.app.main import app

# Create a single in-memory engine shared across all tests.
# StaticPool ensures the same connection is reused so in-memory
# tables persist between get_db() calls.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestSession = sessionmaker(bind=_engine, autocommit=False, autoflush=False)


def _override_get_db():
    db = _TestSession()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = _override_get_db


@pytest.fixture(autouse=True)
def _reset_db():
    """Create fresh tables for each test."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


client = TestClient(app)


class TestStudentsAPI:
    def test_create_student(self):
        resp = client.post("/api/students", json={"name": "Alice", "email": "a@b.com"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Alice"
        assert data["id"] is not None

    def test_list_students(self):
        client.post("/api/students", json={"name": "Bob"})
        resp = client.get("/api/students")
        assert resp.status_code == 200
        assert len(resp.json()) >= 1

    def test_get_student(self):
        create_resp = client.post("/api/students", json={"name": "Carol"})
        sid = create_resp.json()["id"]
        resp = client.get(f"/api/students/{sid}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Carol"

    def test_get_missing_student(self):
        resp = client.get("/api/students/9999")
        assert resp.status_code == 404


class TestProgressAPI:
    def _create_student(self):
        resp = client.post("/api/students", json={"name": "ProgressTest"})
        return resp.json()["id"]

    def test_get_skills_tree(self):
        sid = self._create_student()
        resp = client.get(f"/api/progress/{sid}/skills")
        assert resp.status_code == 200
        tree = resp.json()
        assert len(tree) >= 1  # at least the root node

    def test_get_progress_summary(self):
        sid = self._create_student()
        resp = client.get(f"/api/progress/{sid}/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "total_sessions" in data
        assert "overall_mastery" in data
        assert "mastery_data" in data
        assert isinstance(data["mastery_data"], list)

    def test_get_sessions_empty(self):
        sid = self._create_student()
        resp = client.get(f"/api/progress/{sid}/sessions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_missing_student_404(self):
        resp = client.get("/api/progress/9999/summary")
        assert resp.status_code == 404


class TestChatAPI:
    def test_reset_chat(self):
        resp = client.post("/api/chat", json={
            "student_id": 1,
            "message": "hello",
            "reset": True,
        })
        assert resp.status_code == 200
        assert "cleared" in resp.json()["response"].lower() or "ready" in resp.json()["response"].lower()


class TestHealthCheck:
    def test_health(self):
        resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

import sqlite3

from fastapi.testclient import TestClient

from backend import main


def test_health_reports_readable_database(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "health.db"))
    main.init_db()

    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_unavailable(monkeypatch):
    def unavailable():
        raise sqlite3.OperationalError("unavailable")

    monkeypatch.setattr(main, "db", unavailable)
    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}


def test_health_returns_503_when_schema_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(main, "DB", str(tmp_path / "empty.db"))
    monkeypatch.setattr(main, "init_db", lambda: None)

    with TestClient(main.app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "error", "database": "unavailable"}

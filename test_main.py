from __future__ import annotations

from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine
from sqlmodel.pool import StaticPool

import main


def make_test_client() -> TestClient:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    main.engine = engine
    return TestClient(main.app)


def test_create_note_success() -> None:
    client = make_test_client()
    resp = client.post("/notes", json={"title": "First", "content": "Hello"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["id"] == 1
    assert data["title"] == "First"
    assert data["content"] == "Hello"


def test_create_note_validation_error() -> None:
    client = make_test_client()
    resp = client.post("/notes", json={"title": "   ", "content": "x"})
    assert resp.status_code == 422


def test_get_notes_empty() -> None:
    client = make_test_client()
    resp = client.get("/notes")
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"] == []
    assert data["count"] == 0
    assert data["total"] == 0


def test_get_note_not_found() -> None:
    client = make_test_client()
    resp = client.get("/notes/999")
    assert resp.status_code == 404


def test_patch_note_success() -> None:
    client = make_test_client()
    created = client.post("/notes", json={"title": "A", "content": "B"}).json()
    note_id = created["id"]

    resp = client.patch(f"/notes/{note_id}", json={"content": "Updated"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "Updated"


def test_patch_note_invalid_title() -> None:
    client = make_test_client()
    created = client.post("/notes", json={"title": "A", "content": "B"}).json()
    note_id = created["id"]

    resp = client.patch(f"/notes/{note_id}", json={"title": "   "})
    assert resp.status_code == 422


def test_delete_note_success() -> None:
    client = make_test_client()
    created = client.post("/notes", json={"title": "A", "content": "B"}).json()
    note_id = created["id"]

    resp = client.delete(f"/notes/{note_id}")
    assert resp.status_code == 204

    resp2 = client.get(f"/notes/{note_id}")
    assert resp2.status_code == 404


def test_delete_note_not_found() -> None:
    client = make_test_client()
    resp = client.delete("/notes/999")
    assert resp.status_code == 404


def test_pagination_if_implemented() -> None:
    client = make_test_client()
    for i in range(15):
        client.post("/notes", json={"title": f"n{i}", "content": "x"})

    resp = client.get("/notes?limit=10&offset=0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 10
    assert data["total"] == 15


def test_search_if_implemented() -> None:
    client = make_test_client()
    client.post("/notes", json={"title": "Buy milk", "content": "2 liters"})
    client.post("/notes", json={"title": "Read book", "content": "chapter one"})

    resp = client.get("/notes/search?q=milk")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["title"] == "Buy milk"

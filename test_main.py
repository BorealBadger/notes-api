from fastapi.testclient import TestClient

import main

client = TestClient(main.app)


def setup_function() -> None:
    main.notes_store.clear()
    main.next_id = 1


def test_create_note_success() -> None:
    response = client.post("/notes", json={"title": "First note", "content": "Hello"})

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == 1
    assert data["title"] == "First note"
    assert data["content"] == "Hello"
    assert data["created_at"].endswith("Z")
    assert data["updated_at"].endswith("Z")


def test_create_note_validation_error() -> None:
    response = client.post("/notes", json={"title": "   "})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_get_notes_empty() -> None:
    response = client.get("/notes")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "count": 0,
        "total": 0,
        "limit": 10,
        "offset": 0,
    }


def test_get_note_not_found() -> None:
    response = client.get("/notes/123")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "note_not_found",
            "message": "Note with id=123 not found",
        }
    }


def test_patch_note_success() -> None:
    create_response = client.post("/notes", json={"title": "Before", "content": "Old"})
    note_id = create_response.json()["id"]

    patch_response = client.patch(f"/notes/{note_id}", json={"title": "After"})

    assert patch_response.status_code == 200
    patched = patch_response.json()
    assert patched["title"] == "After"
    assert patched["content"] == "Old"


def test_patch_note_invalid_title() -> None:
    create_response = client.post("/notes", json={"title": "Valid"})
    note_id = create_response.json()["id"]

    patch_response = client.patch(f"/notes/{note_id}", json={"title": ""})

    assert patch_response.status_code == 422
    assert patch_response.json()["error"]["code"] == "validation_error"


def test_delete_note_success() -> None:
    create_response = client.post("/notes", json={"title": "To delete"})
    note_id = create_response.json()["id"]

    delete_response = client.delete(f"/notes/{note_id}")
    get_response = client.get(f"/notes/{note_id}")

    assert delete_response.status_code == 204
    assert delete_response.text == ""
    assert get_response.status_code == 404


def test_delete_note_not_found() -> None:
    response = client.delete("/notes/999")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "note_not_found"


def test_pagination_if_implemented() -> None:
    for i in range(1, 6):
        client.post("/notes", json={"title": f"Note {i}", "content": f"Body {i}"})

    response = client.get("/notes", params={"limit": 2, "offset": 1})

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert data["total"] == 5
    assert data["limit"] == 2
    assert data["offset"] == 1
    assert data["items"][0]["title"] == "Note 2"
    assert data["items"][1]["title"] == "Note 3"


def test_search_if_implemented() -> None:
    client.post("/notes", json={"title": "Shopping", "content": "Buy milk"})
    client.post("/notes", json={"title": "Work", "content": "Prepare demo"})
    client.post("/notes", json={"title": "Ideas", "content": "shopping app feature"})

    response = client.get("/notes/search", params={"q": "shop"})

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["title"] == "Shopping"
    assert data[1]["title"] == "Ideas"

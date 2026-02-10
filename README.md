![CI](https://github.com/BorealBadger/notes-api/actions/workflows/ci.yml/badge.svg)

# Notes Service (FastAPI)

A minimal, beginner-friendly REST API for managing notes using FastAPI and in-memory storage.

## Features

- Create, list (with pagination), fetch, update, and delete notes
- Search notes by text in title/content
- Consistent JSON error contract for 4xx responses
- In-memory data store for v1 (no database yet)

## Requirements

- Python 3.11+

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run the API

```bash
uvicorn main:app --reload
```

API base URL: `http://127.0.0.1:8000`

## Run tests

```bash
pytest -q
```

## API Endpoints

### `POST /notes`
Create a note.

Request body:

```json
{
  "title": "My note",
  "content": "optional text"
}
```

Response: `201 Created`

### `GET /notes?limit=10&offset=0`
List notes with pagination.

Response:

```json
{
  "items": [],
  "count": 0,
  "total": 0,
  "limit": 10,
  "offset": 0
}
```

### `GET /notes/{note_id}`
Get a single note.

Response: `200 OK` or `404 Not Found`

### `PATCH /notes/{note_id}`
Partially update `title` and/or `content`.

Response: `200 OK`, `400 Bad Request` (empty patch), `404 Not Found`, or `422 Validation Error`

### `DELETE /notes/{note_id}`
Delete a note.

Response: `204 No Content` or `404 Not Found`

### `GET /notes/search?q=text`
Search notes by case-insensitive substring in title or content.

Response: `200 OK`

## Error Shape (4xx)

```json
{
  "error": {
    "code": "string_code",
    "message": "Human-readable explanation"
  }
}
```

## Notes

- Data resets whenever the server restarts.
- This is intentionally small for learning and can be extended with a DB/auth later.
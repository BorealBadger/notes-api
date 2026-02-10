from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, field_validator

app = FastAPI(title="Notes Service", version="1.0.0")


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail


class Note(BaseModel):
    id: int
    title: str
    content: str = ""
    created_at: str
    updated_at: str


class CreateNoteRequest(BaseModel):
    title: str
    content: str = ""

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("Title must be a non-empty string")
        return value


class UpdateNoteRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

    @field_validator("title")
    @classmethod
    def title_if_provided_must_not_be_empty(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("Title must be a non-empty string")
        return value


class PaginatedNotesResponse(BaseModel):
    items: List[Note]
    count: int
    total: int
    limit: int
    offset: int


notes_store: Dict[int, Note] = {}
next_id = 1


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def create_note(title: str, content: str = "") -> Note:
    global next_id
    now = utc_now_iso()
    note = Note(
        id=next_id, title=title, content=content, created_at=now, updated_at=now
    )
    notes_store[next_id] = note
    next_id += 1
    return note


def list_notes(limit: int, offset: int) -> PaginatedNotesResponse:
    all_notes = [notes_store[note_id] for note_id in sorted(notes_store)]
    paged_items = all_notes[offset : offset + limit]
    return PaginatedNotesResponse(
        items=paged_items,
        count=len(paged_items),
        total=len(all_notes),
        limit=limit,
        offset=offset,
    )


def get_note_by_id(note_id: int) -> Optional[Note]:
    return notes_store.get(note_id)


def update_note(
    note_id: int, title: Optional[str], content: Optional[str]
) -> Optional[Note]:
    note = notes_store.get(note_id)
    if note is None:
        return None

    changed = False
    updated_values = note.model_dump()

    if title is not None and title != note.title:
        updated_values["title"] = title
        changed = True
    if content is not None and content != note.content:
        updated_values["content"] = content
        changed = True

    if changed:
        updated_values["updated_at"] = utc_now_iso()

    updated_note = Note(**updated_values)
    notes_store[note_id] = updated_note
    return updated_note


def delete_note(note_id: int) -> bool:
    if note_id not in notes_store:
        return False
    del notes_store[note_id]
    return True


def search_notes(query: str) -> List[Note]:
    q = query.lower()
    all_notes = [notes_store[note_id] for note_id in sorted(notes_store)]
    return [
        note
        for note in all_notes
        if q in note.title.lower() or q in note.content.lower()
    ]


def error_response(status_code: int, code: str, message: str) -> JSONResponse:
    payload = ErrorResponse(error=ErrorDetail(code=code, message=message)).model_dump()
    return JSONResponse(status_code=status_code, content=payload)


@app.exception_handler(HTTPException)
async def http_exception_handler(_: Request, exc: HTTPException) -> JSONResponse:
    if isinstance(exc.detail, dict) and "error" in exc.detail:
        return JSONResponse(status_code=exc.status_code, content=exc.detail)
    return error_response(exc.status_code, "http_error", str(exc.detail))


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    _: Request, exc: RequestValidationError
) -> JSONResponse:
    first_error = exc.errors()[0]
    message = first_error.get("msg", "Validation error")
    return error_response(status_code=422, code="validation_error", message=message)


@app.post("/notes", response_model=Note, status_code=201)
def post_note(payload: CreateNoteRequest) -> Note:
    return create_note(title=payload.title.strip(), content=payload.content)


@app.get("/notes", response_model=PaginatedNotesResponse)
def get_notes(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginatedNotesResponse:
    return list_notes(limit=limit, offset=offset)


@app.get("/notes/search", response_model=List[Note])
def get_notes_search(q: str = Query(..., min_length=1)) -> List[Note]:
    return search_notes(q)


@app.get("/notes/{note_id}", response_model=Note)
def get_note(note_id: int) -> Note:
    note = get_note_by_id(note_id)
    if note is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="note_not_found", message=f"Note with id={note_id} not found"
                )
            ).model_dump(),
        )
    return note


@app.patch("/notes/{note_id}", response_model=Note)
def patch_note(note_id: int, payload: UpdateNoteRequest) -> Note:
    if payload.title is None and payload.content is None:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="invalid_request",
                    message="Provide at least one field to update: title or content",
                )
            ).model_dump(),
        )

    note = update_note(
        note_id=note_id,
        title=payload.title.strip() if payload.title is not None else None,
        content=payload.content,
    )
    if note is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="note_not_found", message=f"Note with id={note_id} not found"
                )
            ).model_dump(),
        )
    return note


@app.delete("/notes/{note_id}", status_code=204)
def remove_note(note_id: int) -> None:
    deleted = delete_note(note_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                error=ErrorDetail(
                    code="note_not_found", message=f"Note with id={note_id} not found"
                )
            ).model_dump(),
        )
    return None

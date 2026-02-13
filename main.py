from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Header, HTTPException, Query, Response
from pydantic import BaseModel, field_validator
from sqlmodel import Field, Session, SQLModel, create_engine, select

app = FastAPI(
    title="Notes API",
    version="1.1.0",
    description="Simple notes service with SQLite persistence, search, and health checks.",
    contact={"name": "BorealBadger"},
    openapi_tags=[
        {"name": "health", "description": "Service health endpoints"},
        {"name": "notes", "description": "CRUD and search operations for notes"},
    ],
)

API_KEY = os.getenv("NOTES_API_KEY", "dev-secret-key")  # change in production


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Unauthorized")


def not_found_error(entity: str = "Note") -> HTTPException:
    return HTTPException(
        status_code=404,
        detail={"error": {"code": "not_found", "message": f"{entity} not found"}},
    )


# ---------- Database ----------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///notes.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


def utc_now_iso() -> str:
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


class Note(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str
    content: str = ""
    created_at: str
    updated_at: str


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


@app.on_event("startup")
def on_startup() -> None:
    create_db_and_tables()


# ---------- API Schemas ----------
class CreateNoteRequest(BaseModel):
    title: str
    content: str = ""

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title must be a non-empty string")
        return v.strip()


class PatchNoteRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title must be a non-empty string")
        return v.strip() if v is not None else v


class NoteResponse(BaseModel):
    id: int
    title: str
    content: str
    created_at: str
    updated_at: str


class PaginatedNotesResponse(BaseModel):
    items: list[NoteResponse]
    count: int
    total: int
    limit: int
    offset: int


def to_note_response(note: Note) -> NoteResponse:
    return NoteResponse(
        id=note.id or 0,
        title=note.title,
        content=note.content,
        created_at=note.created_at,
        updated_at=note.updated_at,
    )


# ---------- Routes ----------
@app.post("/notes", response_model=NoteResponse, status_code=201)
def create_note(payload: CreateNoteRequest) -> NoteResponse:
    now = utc_now_iso()
    note = Note(
        title=payload.title,
        content=payload.content,
        created_at=now,
        updated_at=now,
    )
    with Session(engine) as session:
        session.add(note)
        session.commit()
        session.refresh(note)
        return to_note_response(note)


@app.get("/notes", response_model=PaginatedNotesResponse)
def list_notes(
    limit: int = Query(default=10, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> PaginatedNotesResponse:
    with Session(engine) as session:
        total = len(session.exec(select(Note)).all())
        notes = session.exec(select(Note).offset(offset).limit(limit)).all()
        items = [to_note_response(n) for n in notes]
        return PaginatedNotesResponse(
            items=items,
            count=len(items),
            total=total,
            limit=limit,
            offset=offset,
        )


# IMPORTANT: keep /notes/search BEFORE /notes/{note_id}
@app.get("/notes/search", response_model=list[NoteResponse])
def search_notes(q: str = Query(..., min_length=1)) -> list[NoteResponse]:
    q_lower = q.lower()
    with Session(engine) as session:
        notes = session.exec(select(Note)).all()
        filtered = [
            n
            for n in notes
            if q_lower in n.title.lower() or q_lower in n.content.lower()
        ]
        return [to_note_response(n) for n in filtered]


@app.get("/notes/{note_id}", response_model=NoteResponse)
def get_note(note_id: int) -> NoteResponse:
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            raise not_found_error("Note")
        return to_note_response(note)


@app.patch("/notes/{note_id}", response_model=NoteResponse)
def patch_note(note_id: int, payload: PatchNoteRequest) -> NoteResponse:
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            raise not_found_error("Note")

        if payload.title is not None:
            note.title = payload.title
        if payload.content is not None:
            note.content = payload.content

        note.updated_at = utc_now_iso()
        session.add(note)
        session.commit()
        session.refresh(note)
        return to_note_response(note)


@app.delete("/notes/{note_id}", status_code=204, response_class=Response)
def delete_note(note_id: int) -> Response:
    with Session(engine) as session:
        note = session.get(Note, note_id)
        if not note:
            raise not_found_error("Note")

        session.delete(note)
        session.commit()
        return Response(status_code=204)


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}

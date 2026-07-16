# Phase 3 - schemas.py
# Pydantic request/response schemas

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    email: EmailStr
    question: str
    user_id: int | None = None   # omit to start a new session


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class MessageOut(BaseModel):
    role: str
    content: str


class ChatResponse(BaseModel):
    email: EmailStr
    answer: str
    sources: list[str]
    history: list[MessageOut]


class SessionOut(BaseModel):
    # session_id: int
    created_at: str


class HealthResponse(BaseModel):
    status: str

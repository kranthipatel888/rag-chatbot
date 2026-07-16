# schemas.py
# Pydantic request/response schemas

from pydantic import BaseModel, EmailStr


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    email: EmailStr
    question: str


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


class HealthResponse(BaseModel):
    status: str

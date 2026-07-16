# main.py
# FastAPI app — routes only, no business logic here

import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from chat import build_rag_chain
from database import get_db, init_db
from schemas import ChatRequest, ChatResponse, HealthResponse, MessageOut

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------

rag_chain = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global rag_chain
    await init_db()
    rag_chain = build_rag_chain()
    print("RAG chain ready.")
    yield

app = FastAPI(title="RAG Chatbot API", version="1.0.0", lifespan=lifespan)

# Serve static files (chat UI) from the /static folder
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/", include_in_schema=False)
async def serve_ui():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/health", response_model=HealthResponse)
async def health():
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # 1. Resolve or create user by email
    user_id = await crud.get_user_id_by_email(db, req.email)
    if not user_id:
        user = await crud.create_user(db, req.email)
        user_id = user.id

    # 2. Load history and build context string
    history_rows = await crud.get_history(db, user_id)
    history_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in history_rows)

    # 3. Augment question with conversation history
    augmented_question = (
        f"Conversation so far:\n{history_text}\n\nNew question: {req.question}"
        if history_text
        else req.question
    )

    # 4. Run RAG chain
    result = rag_chain.invoke({"input": augmented_question})
    answer = result["answer"]

    # 5. Persist both turns sequentially
    await crud.save_message(db, user_id, "user", req.question)
    await crud.save_message(db, user_id, "bot", answer)

    # 6. Build response
    updated_history = await crud.get_history(db, user_id)
    sources = sorted({
        doc.metadata.get("source", "unknown")
        for doc in result.get("context", [])
    })

    return ChatResponse(
        email=req.email,
        answer=answer,
        sources=sources,
        history=[MessageOut(role=m.role, content=m.content) for m in updated_history],
    )


@app.get("/api/history/email/{email}", response_model=list[MessageOut])
async def history_by_email(email: str, db: AsyncSession = Depends(get_db)):
    """Return the full message history by email."""
    user_id = await crud.get_user_id_by_email(db, email)
    if user_id is None:
        raise HTTPException(status_code=404, detail=f"User '{email}' not found.")
    rows = await crud.get_history(db, user_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No history found for this user.")
    return [MessageOut(role=m.role, content=m.content) for m in rows]


@app.get("/api/history/id/{user_id}", response_model=list[MessageOut])
async def history_by_id(user_id: int, db: AsyncSession = Depends(get_db)):
    """Return the full message history by user ID."""
    rows = await crud.get_history(db, user_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No history found for this user.")
    return [MessageOut(role=m.role, content=m.content) for m in rows]

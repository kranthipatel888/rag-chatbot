# main.py
# FastAPI app — routes only, no business logic here

import json
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.ext.asyncio import AsyncSession

import crud
from chat import build_rag_chain, stream_rag_response
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


@app.post("/api/chat/stream")
async def chat_stream(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """
    Streaming endpoint — returns Server-Sent Events.
    Each event is a JSON object:
      { "token": "..." }          — partial token
      { "done": true, "sources": [...] }  — end of stream
    """
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    # Resolve or create user
    user_id = await crud.get_user_id_by_email(db, req.email)
    if not user_id:
        user = await crud.create_user(db, req.email)
        user_id = user.id

    # Load history and build augmented question
    history_rows = await crud.get_history(db, user_id)
    history_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in history_rows)
    augmented_question = (
        f"Conversation so far:\n{history_text}\n\nNew question: {req.question}"
        if history_text
        else req.question
    )

    async def event_generator():
        full_answer = []
        final_sources = []

        async for token, sources in stream_rag_response(augmented_question):
            if token:
                full_answer.append(token)
                yield f"data: {json.dumps({'token': token})}\n\n"
            else:
                # Final sentinel — save to DB and send done event
                final_sources = sources
                answer = "".join(full_answer)
                await crud.save_message(db, user_id, "user", req.question)
                await crud.save_message(db, user_id, "bot", answer)
                yield f"data: {json.dumps({'done': True, 'sources': final_sources})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disables Nginx buffering on Railway
        },
    )


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest, db: AsyncSession = Depends(get_db)):
    """Non-streaming endpoint — kept for Swagger testing."""
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    user_id = await crud.get_user_id_by_email(db, req.email)
    if not user_id:
        user = await crud.create_user(db, req.email)
        user_id = user.id

    history_rows = await crud.get_history(db, user_id)
    history_text = "\n".join(f"{m.role.upper()}: {m.content}" for m in history_rows)
    augmented_question = (
        f"Conversation so far:\n{history_text}\n\nNew question: {req.question}"
        if history_text
        else req.question
    )

    result = rag_chain.invoke({"input": augmented_question})
    answer = result["answer"]

    await crud.save_message(db, user_id, "user", req.question)
    await crud.save_message(db, user_id, "bot", answer)

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
    user_id = await crud.get_user_id_by_email(db, email)
    if user_id is None:
        raise HTTPException(status_code=404, detail=f"User '{email}' not found.")
    rows = await crud.get_history(db, user_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No history found for this user.")
    return [MessageOut(role=m.role, content=m.content) for m in rows]


@app.get("/api/history/id/{user_id}", response_model=list[MessageOut])
async def history_by_id(user_id: int, db: AsyncSession = Depends(get_db)):
    rows = await crud.get_history(db, user_id)
    if not rows:
        raise HTTPException(status_code=404, detail="No history found for this user.")
    return [MessageOut(role=m.role, content=m.content) for m in rows]

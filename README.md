# RAG Chatbot

A production-ready conversational AI built with LangChain, Pinecone, Gemini, FastAPI, and Neon Postgres. Users chat via a clean web UI, and all conversation history is persisted per email address across sessions.

## Architecture

```
User (Browser)
    ↓
FastAPI (Railway)
    ├── Pinecone Cloud   — vector store for markdown knowledge base
    ├── Gemini           — embeddings (gemini-embedding-001) + LLM (gemini-2.5-flash)
    └── Neon Postgres    — persistent chat history per user (email-keyed)
```

## Features

- RAG pipeline over your own Markdown docs
- Per-user chat history — same email picks up where you left off
- Clean dark-themed chat UI served at `/`
- REST API with Swagger docs at `/docs`
- Deployed on Railway with Neon (no local DB needed in production)

## Project Structure

```
rag-chatbot/
├── src/
│   ├── main.py        # FastAPI routes
│   ├── chat.py        # RAG chain (Pinecone + Gemini)
│   ├── ingest.py      # Load markdown → embed → upload to Pinecone
│   ├── database.py    # Async engine + session factory
│   ├── models.py      # SQLAlchemy models (User, Message)
│   ├── schemas.py     # Pydantic request/response schemas
│   ├── crud.py        # DB query functions
│   └── static/
│       └── index.html # Chat UI
├── data/              # Put your .md files here
├── app.py             # Railway entrypoint
├── Procfile
├── railway.json
├── requirements.txt
└── .env.example
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Chat UI |
| GET | `/health` | Health check |
| POST | `/api/chat` | Send a message, get an answer |
| GET | `/api/history/email/{email}` | Full chat history by email |
| GET | `/api/history/id/{user_id}` | Full chat history by user ID |

### POST `/api/chat`

```json
{
  "email": "you@example.com",
  "question": "What are your pricing tiers?"
}
```

Response includes `answer`, `sources`, `session_id`, and full `history`.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GOOGLE_API_KEY` | Gemini API key — [get one here](https://aistudio.google.com/app/apikey) |
| `PINECONE_API_KEY` | Pinecone API key — [app.pinecone.io](https://app.pinecone.io) |
| `PINECONE_INDEX_NAME` | Name of your Pinecone index (dimension: 768, metric: cosine) |
| `DATABASE_URL` | Neon connection string (`postgresql://...?sslmode=require`) |

For local Postgres instead of Neon, you can use individual vars:
`DATABASE_HOSTNAME`, `DATABASE_PORT`, `DATABASE_USERNAME`, `DATABASE_PASSWORD`, `DATABASE_NAME`

## Local Setup

```bash
# 1. Clone and create virtual environment
python -m venv .venv
.venv\Scripts\activate       # Windows
# source .venv/bin/activate  # Mac/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
copy .env.example .env       # Windows
# cp .env.example .env       # Mac/Linux
# Fill in all 4 env vars in .env

# 4. Add your Markdown docs
# Drop .md files into data/

# 5. Ingest docs into Pinecone
python src/ingest.py

# 6. Start the server
python run.py
```

Open `http://localhost:8000` for the chat UI or `http://localhost:8000/docs` for Swagger.

## Pinecone Index Setup

Create your index at [app.pinecone.io](https://app.pinecone.io) with:
- **Dimension:** 768
- **Metric:** cosine
- **Cloud:** AWS, Region: us-east-1

Then run `python src/ingest.py` to populate it with your docs.

## Deployment (Railway)

1. Push to GitHub
2. New Project → Deploy from GitHub repo
3. Add the 4 environment variables in the Variables tab
4. Railway auto-deploys on every push

## Tech Stack

- **LangChain** — RAG orchestration
- **Pinecone** — Cloud vector store
- **Gemini** — Embeddings + LLM (Google)
- **FastAPI** — API server
- **SQLAlchemy + asyncpg** — Async database layer
- **Neon** — Serverless Postgres
- **Railway** — Deployment platform

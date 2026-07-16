# RAG Chatbot — Phase 1: RAG Core (LangChain + ChromaDB)

## Setup

1. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate   # Mac/Linux: source venv/bin/activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set your Gemini API key**
   ```bash
   copy .env.example .env
   ```
   Edit `.env` and paste your key:
   ```
   GOOGLE_API_KEY=your_actual_key_here
   ```
   Get a key at https://aistudio.google.com/app/apikey

4. **Add Markdown files**
   Drop one or more `.md` files into the `data/` folder.

## Run

**Step 1 — Ingest docs (load → embed → store vectors):**
```bash
python src/ingest.py
```

**Step 2 — Chat (Q&A chain, terminal test):**
```bash
python src/chat.py
```
Ask questions about your Markdown files. Type `exit` to quit.

## Project structure
```
rag-chatbot/
├── data/           # put your .md files here
├── chroma_db/      # persisted vector store (auto-generated)
├── src/
│   ├── ingest.py   # load → embed → store
│   └── chat.py     # retrieval + Q&A chain
├── requirements.txt
├── .env.example
└── README.md
```

## Next: Phase 2
Database layer (Neon + SQLAlchemy + asyncpg) to persist chat history.

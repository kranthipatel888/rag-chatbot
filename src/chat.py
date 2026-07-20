"""
chat.py — RAG chain + streaming helper
"""
import os
from typing import AsyncGenerator

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()

INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")

SYSTEM_PROMPT = (
    "You are a helpful assistant answering questions using only the provided context. "
    "If the answer isn't in the context, say you don't know — don't make things up.\n\n"
    "Context:\n{context}"
)


def _build_components():
    """Shared embeddings, vectorstore, retriever, llm, prompt."""
    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
    vectorstore = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("human", "{input}"),
    ])
    return retriever, llm, prompt


def build_rag_chain():
    """Non-streaming chain — used for terminal testing."""
    retriever, llm, prompt = _build_components()
    combine_docs_chain = create_stuff_documents_chain(llm, prompt)
    return create_retrieval_chain(retriever, combine_docs_chain)


async def stream_rag_response(question: str) -> AsyncGenerator[tuple[str, list], None]:
    """
    Retrieve relevant docs, then stream LLM tokens one by one.
    Yields: (token, sources) where sources is [] until the final chunk.
    Final chunk: ("", sources_list) signals end of stream.
    """
    retriever, llm, prompt = _build_components()

    # Step 1 — retrieve docs (non-streaming)
    docs = await retriever.ainvoke(question)
    sources = sorted({
        doc.metadata.get("source", "unknown") for doc in docs
    })

    # Step 2 — build context string from docs
    context = "\n\n".join(doc.page_content for doc in docs)

    # Step 3 — build prompt messages
    messages = prompt.format_messages(input=question, context=context)

    # Step 4 — stream LLM tokens
    async for chunk in llm.astream(messages):
        token = chunk.content
        if token:
            yield token, []

    # Step 5 — final sentinel with sources
    yield "", sources


def main():
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY not set.")
    if not os.getenv("PINECONE_API_KEY") or not INDEX_NAME:
        raise RuntimeError("Pinecone config missing.")

    rag_chain = build_rag_chain()
    print(f"Connected to '{INDEX_NAME}'. Type your question (or 'exit').\n")
    while True:
        query = input("You: ").strip()
        if query.lower() in {"exit", "quit"}:
            print("Bye!")
            break
        if not query:
            continue
        result = rag_chain.invoke({"input": query})
        print(f"\nBot: {result['answer']}\n")
        sources = {doc.metadata.get("source", "unknown") for doc in result.get("context", [])}
        if sources:
            print(f"  (sources: {', '.join(sorted(sources))})\n")


if __name__ == "__main__":
    main()

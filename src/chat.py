"""
Phase 1 - Step 2: Q&A chain over the Pinecone Cloud vector store, tested in terminal.

Run: python src/chat.py
"""
import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings, ChatGoogleGenerativeAI
from langchain_pinecone import PineconeVectorStore  # Updated Import
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


def build_rag_chain():
    # Setup Gemini Embeddings (Must match the 768 dimension layout used during ingestion)
    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

    # Connect directly to your live Pinecone Cloud Instance
    vectorstore = PineconeVectorStore(
        index_name=INDEX_NAME,
        embedding=embeddings
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.2)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            ("human", "{input}"),
        ]
    )

    combine_docs_chain = create_stuff_documents_chain(llm, prompt)
    rag_chain = create_retrieval_chain(retriever, combine_docs_chain)
    return rag_chain


def main():
    # Structural Checkpoints
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError(
            "GOOGLE_API_KEY not set. Copy .env.example to .env and add your Gemini API key."
        )

    if not os.getenv("PINECONE_API_KEY") or not os.getenv("PINECONE_INDEX_NAME"):
        raise RuntimeError(
            "Pinecone configurations (PINECONE_API_KEY or PINECONE_INDEX_NAME) are missing from your .env file."
        )

    rag_chain = build_rag_chain()

    print(f"RAG chatbot connected to cloud index '{INDEX_NAME}' ready. Type your question (or 'exit' to quit).\n")
    while True:
        query = input("You: ").strip()
        if query.lower() in {"exit", "quit"}:
            print("Bye!")
            break
        if not query:
            continue

        result = rag_chain.invoke({"input": query})
        print(f"\nBot: {result['answer']}\n")

        sources = {
            doc.metadata.get("source", "unknown")
            for doc in result.get("context", [])
        }
        if sources:
            print(f"  (sources: {', '.join(sorted(sources))})\n")


if __name__ == "__main__":
    main()
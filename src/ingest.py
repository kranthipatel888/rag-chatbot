"""
Phase 1 - Step 1: Ingest Markdown files into Pinecone Cloud
Loads all Markdown files from ./data, splits into chunks, embeds with Gemini,
and upserts vectors to a managed Pinecone Index.

Run: python src/ingest.py
"""
import os
from dotenv import load_dotenv
from langchain_community.document_loaders import TextLoader, DirectoryLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore  # Updated Import
from langchain_core.documents import Document

load_dotenv()

DATA_DIR = "data"
INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")


def load_documents():
    print(f"Loading Markdown files from '{DATA_DIR}/'...")
    loader = DirectoryLoader(
        DATA_DIR,
        glob="**/*.md",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"},
        show_progress=True,
    )
    docs = loader.load()
    print(f"Loaded {len(docs)} Markdown file(s).")
    return docs


def split_documents(docs):
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    chunks = []
    for doc in docs:
        # 1. Split the raw text string of the document
        header_chunks = splitter.split_text(doc.page_content)
        
        # 2. Merge the original document metadata with the new header metadata
        for chunk in header_chunks:
            # Combine original metadata (e.g., source file path) with the header info
            combined_metadata = {**doc.metadata, **chunk.metadata}
            
            # Create a new Document object and add it to our final list
            chunks.append(Document(page_content=chunk.page_content, metadata=combined_metadata))
            
    print(f"Split into {len(chunks)} chunks.")
    return chunks

def embed_and_store(chunks):
    # Setup Gemini Embeddings
    embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")

    print(f"Embedding chunks and uploading to Pinecone Index '{INDEX_NAME}' (running cloud network operations)...")
    
    # Ingest data directly into your Pinecone Cloud Instance
    vectorstore = PineconeVectorStore.from_documents(
        documents=chunks,
        embedding=embeddings,
        index_name=INDEX_NAME
    )
    
    print(f"Successfully uploaded {len(chunks)} vectors to Pinecone Cloud!")
    return vectorstore


def main():
    # Structural Checkpoints
    if not os.getenv("GOOGLE_API_KEY"):
        raise RuntimeError("GOOGLE_API_KEY not set in .env file.")
        
    if not os.getenv("PINECONE_API_KEY") or not os.getenv("PINECONE_INDEX_NAME"):
        raise RuntimeError("Pinecone environment variables (API Key or Index Name) are missing from your configuration.")

    if not os.path.isdir(DATA_DIR) or not any(
        f.lower().endswith(".md") for f in os.listdir(DATA_DIR)
    ):
        raise RuntimeError(
            f"No Markdown files found in '{DATA_DIR}/'. Add at least one .md file and re-run."
        )

    docs = load_documents()
    chunks = split_documents(docs)
    embed_and_store(chunks)
    print("\nCloud Ingestion complete. You are ready to update your chat engine settings next!")


if __name__ == "__main__":
    main()
from brain.rag.ingestion import ingest_chunks
from brain.rag.loader import load_documents
from brain.rag.splitter import split_documents
from brain.rag.vectordb import collection


def build_database(data_path: str):

    print("=" * 80)
    print("LOADING DOCUMENTS")
    print("=" * 80)

    docs = load_documents(data_path)
    print(f"Loaded {len(docs)} documents")

    print()
    print("=" * 80)
    print("SPLITTING")
    print("=" * 80)

    chunks = split_documents(docs)
    print(f"Created {len(chunks)} chunks")

    print()
    print("=" * 80)
    print("INGESTING INTO CHROMA")
    print("=" * 80)

    sources_updated, total = ingest_chunks(collection, chunks)

    print(f"Updated {sources_updated} sources / {total} chunks")

    print()
    print("=" * 80)
    print("DATABASE BUILD COMPLETE")
    print("=" * 80)

    return total

from __future__ import annotations

import logging

from brain.rag.ingestion import ingest_chunks
from brain.rag.loader import load_documents
from brain.rag.splitter import split_documents
from brain.rag.vectordb import collection


logger = logging.getLogger(__name__)


def build_database(data_path):

    logger.info("Loading documents...")
    docs = load_documents(data_path)
    logger.info("Loaded %d documents", len(docs))

    logger.info("Splitting...")
    chunks = split_documents(docs)
    logger.info("Created %d chunks", len(chunks))

    logger.info("Ingesting into Chroma...")

    sources_updated, total = ingest_chunks(collection, chunks)

    logger.info("Updated %d sources / %d chunks", sources_updated, total)

    return total

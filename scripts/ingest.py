import uuid
from pathlib import Path

import fitz

from noisyne.embedding import embedding_model
from noisyne.chroma import knowledge

PDF_FOLDER = Path(r"E:\SoundBrain\data\courses\psychoacoustics")


def chunk_text(text, chunk_size=700, overlap=100):
    chunks = []

    start = 0

    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start += chunk_size - overlap

    return chunks


for pdf_file in PDF_FOLDER.glob("*.pdf"):

    print(f"Reading {pdf_file.name}")

    doc = fitz.open(pdf_file)

    for page_number, page in enumerate(doc):

        text = page.get_text()

        if not text.strip():
            continue

        chunks = chunk_text(text)

        for chunk in chunks:

            embedding = embedding_model.encode(chunk).tolist()

            knowledge.add(
                ids=[str(uuid.uuid4())],
                documents=[chunk],
                embeddings=[embedding],
                metadatas=[{
                    "source": pdf_file.name,
                    "page": page_number + 1
                }]
            )

print("✅ Finished")
print(f"Database Count : {knowledge.count()}")
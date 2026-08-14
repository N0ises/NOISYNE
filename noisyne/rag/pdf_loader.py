import fitz
from pathlib import Path
from langchain_core.documents import Document


def load_pdf(path):

    doc = fitz.open(path)

    documents = []

    for page_number, page in enumerate(doc):

        text = page.get_text("text")

        documents.append(
            Document(
                page_content=text,
                metadata={
                    "source": str(path),
                    "page": page_number + 1,
                },
            )
        )

    return documents
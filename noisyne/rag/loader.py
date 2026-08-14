import re
from pathlib import Path

from langchain_core.documents import Document

from noisyne.rag.pdf_loader import load_pdf


def clean_text(text: str) -> str:

    text = text.replace("\x00", "")

    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)

    text = text.strip()

    return text


def load_documents(data_path: str):

    documents = []

    data_path = Path(data_path)

    for pdf in sorted(data_path.rglob("*.pdf")):

        print(f"Loading {pdf.name}")

        pages = load_pdf(str(pdf))

        for page in pages:

            if isinstance(page, Document):

                text = clean_text(page.page_content)

                if len(text) < 30:
                    continue

                page.page_content = text
                documents.append(page)

            else:

                text = clean_text(page["text"])

                if len(text) < 30:
                    continue

                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "source": page["source"],
                            "page": page["page"],
                        },
                    )
                )

    print(f"Loaded {len(documents)} documents.")

    return documents
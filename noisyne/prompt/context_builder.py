from __future__ import annotations


class ContextBuilder:

    def build(
        self,
        documents,
    ) -> str:

        if not documents:
            return ""

        chunks = []

        for i, doc in enumerate(documents, start=1):

            if hasattr(doc, "text"):

                text = doc.text

            else:

                text = str(doc)

            if hasattr(doc, "source"):

                source = doc.source

            else:

                source = "Unknown"

            if hasattr(doc, "page"):

                page = doc.page

            else:

                page = "-"

            chunks.append(
                f"""[Document {i}]
Source: {source}
Page: {page}

{text}"""
            )

        return "\n\n------------------------\n\n".join(chunks)
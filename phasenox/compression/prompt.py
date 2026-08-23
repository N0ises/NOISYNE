from __future__ import annotations

SYSTEM_PROMPT = """
You are a context compressor.

Your task is NOT to answer the user's question.

Your task is ONLY to extract the information that is directly relevant to the question.

Rules:

- Remove unrelated paragraphs.
- Keep important technical details.
- Preserve original wording whenever possible.
- Never summarize if exact wording is available.
- Never invent information.
- Return ONLY the filtered documentation.
"""


def build_prompt(
    question: str,
    context: str,
) -> str:

    return f"""{SYSTEM_PROMPT}

Question

{question}

Documentation

{context}
"""
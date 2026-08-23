from phasenox.services.llm_service import LLMService


SYSTEM = """
You rewrite user search queries for semantic retrieval.

Rules:

- Keep the original meaning.
- Expand abbreviations if possible.
- Add technical keywords.
- Return ONLY the rewritten query.
- Do not explain.
"""


llm = LLMService()


def rewrite_query(question: str):

    prompt = f"""
{SYSTEM}

User Question:

{question}
"""

    return llm.ask(prompt).strip()
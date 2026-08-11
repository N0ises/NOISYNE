from brain.rag.scoring import score_from_distance
from brain.rag.vectordb import collection


def retrieve(query: str, k: int = 10):

    results = collection.query(
        query_texts=[query],
        n_results=k,
    )

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]

    distances = results.get("distances", [[0] * len(documents)])[0]

    output = []

    for doc, meta, distance in zip(documents, metadatas, distances):

        output.append(
            {
                "text": doc,
                "source": meta.get("source", ""),
                "page": meta.get("page", 0),
                "score": score_from_distance(float(distance), metric="cosine"),
            }
        )

    output = sorted(output, key=lambda x: x["score"], reverse=True)

    return output
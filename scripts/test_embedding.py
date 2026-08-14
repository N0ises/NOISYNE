from pathlib import Path

from sentence_transformers import SentenceTransformer

PROJECT_ROOT = Path(__file__).resolve().parent.parent

print("Loading Qwen Embedding...")

model = SentenceTransformer(
    PROJECT_ROOT / "models" / "Qwen3-Embedding-0.6B", trust_remote_code=True
)

print("✅ Model Loaded!")

text = ["سلام من یک مهندس صدا هستم.", "What is psychoacoustics?"]

embeddings = model.encode(text)

print(embeddings.shape)

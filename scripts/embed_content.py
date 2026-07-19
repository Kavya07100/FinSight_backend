"""
scripts/embed_content.py

Takes every passage in literacy_content.py, sends it to Gemini's embedding
model, and stores both the original text and its embedding in the
embedded_content table -- this is what makes RAG retrieval possible later.

Run this once now (to load the initial content), and again any time you
add new passages to literacy_content.py.
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from sqlalchemy import text

from app.database import engine
from scripts.literacy_content import LITERACY_CONTENT

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSIONS = 1536  # matches the vector(1536) column we added


def embed_text(content: str) -> list[float]:
    """
    Calls Gemini to convert a piece of text into a vector.
    task_type="RETRIEVAL_DOCUMENT" tells the model this text is something
    that will be *searched for* later (as opposed to a search query itself)
    -- Gemini optimizes the embedding slightly differently depending on
    which side of the search it expects to be used for.
    """
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=content,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )
    return result.embeddings[0].values


def to_pgvector_literal(embedding: list[float]) -> str:
    """
    pgvector expects vectors as a string like '[0.12,0.34,...]' that gets
    cast to the vector type in SQL. Plain Python lists aren't automatically
    understood by the database driver, so we format it ourselves.
    """
    return "[" + ",".join(str(v) for v in embedding) + "]"


def ingest():
    with engine.connect() as conn:
        for entry in LITERACY_CONTENT:
            print(f"Embedding: {entry['title']}...")
            embedding = embed_text(entry["content"])
            embedding_literal = to_pgvector_literal(embedding)

            conn.execute(
                text("""
                    INSERT INTO embedded_content (source, title, content, tags, embedding)
                    VALUES (:source, :title, :content, :tags, CAST(:embedding AS vector))
                """),
                {
                    "source": "literacy_content",
                    "title": entry["title"],
                    "content": entry["content"],
                    "tags": entry["tags"],
                    "embedding": embedding_literal,
                },
            )
            print(f"  Stored ({len(embedding)} dimensions)")

        conn.commit()

    print("Done.")


if __name__ == "__main__":
    ingest()

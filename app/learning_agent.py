"""
app/learning_agent.py

The Learning Agent's RAG pipeline: given a user's question, retrieves the
most relevant stored passages (via pgvector similarity search) and asks
Gemini to answer using only that retrieved content -- so answers are
grounded in your curated content, not made up from the model's general
training knowledge.

Two steps, matching the standard RAG pattern:
  1. retrieve_relevant_content() -- the "R" (Retrieval)
  2. generate_answer()           -- the "AG" (Augmented Generation)
"""

import os
from dotenv import load_dotenv
from google import genai
from google.genai import types
from groq import Groq
from sqlalchemy import text

from app.database import engine

load_dotenv()

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
groq_client = Groq(api_key=os.environ["GROQ_API_KEY"])

EMBEDDING_MODEL = "gemini-embedding-001"
GENERATION_MODEL = "llama-3.3-70b-versatile"
EMBEDDING_DIMENSIONS = 1536


def embed_query(question: str) -> list[float]:
    """
    Same embedding model as before, but task_type="RETRIEVAL_QUERY" this
    time -- not "RETRIEVAL_DOCUMENT". This is a question being asked, not
    a passage being stored, and Gemini shapes the embedding slightly
    differently depending on which role the text is playing in the search.
    """
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=question,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_QUERY",
            output_dimensionality=EMBEDDING_DIMENSIONS,
        ),
    )
    return result.embeddings[0].values


def retrieve_relevant_content(question: str, top_k: int = 3) -> list[dict]:
    """
    Embeds the question, then asks pgvector for the top_k stored passages
    with the smallest cosine distance (i.e. closest in meaning) to it.
    The <=> operator is pgvector's cosine distance operator -- smaller
    means more similar, which is why we ORDER BY it ascending.
    """
    query_embedding = embed_query(question)
    embedding_literal = "[" + ",".join(str(v) for v in query_embedding) + "]"

    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT title, content, tags,
                       embedding <=> CAST(:query_embedding AS vector) AS distance
                FROM embedded_content
                ORDER BY distance ASC
                LIMIT :top_k
            """),
            {"query_embedding": embedding_literal, "top_k": top_k},
        ).fetchall()

    return [
        {"title": r.title, "content": r.content, "tags": r.tags, "distance": float(r.distance)}
        for r in rows
    ]


def generate_answer(question: str, top_k: int = 3) -> dict:
    """
    Full RAG pipeline: retrieve relevant passages, then ask Gemini to
    answer using ONLY that retrieved content. Returns both the answer
    and which sources were used, so the app can show "based on: ..."
    for transparency.
    """
    retrieved = retrieve_relevant_content(question, top_k=top_k)

    if not retrieved:
        return {
            "answer": "I don't have relevant content to answer that yet.",
            "sources": [],
        }

    context = "\n\n".join(
        f"[{r['title']}]\n{r['content']}" for r in retrieved
    )

    prompt = (
        "Answer the user's question using ONLY the information in the "
        "context below. If the context doesn't contain enough information "
        "to answer, say so honestly rather than guessing. Keep the answer "
        "clear and beginner-friendly.\n\n"
        f"Context:\n{context}\n\n"
        f"Question: {question}"
    )

    response = groq_client.chat.completions.create(
        model=GENERATION_MODEL,
        messages=[{"role": "user", "content": prompt}],
    )

    return {
        "answer": response.choices[0].message.content,
        "sources": [r["title"] for r in retrieved],
    }


if __name__ == "__main__":
    # Manual smoke test -- try a few real questions here.
    result = generate_answer("Why shouldn't I put all my money into one stock?")
    print("Answer:", result["answer"])
    print("\nSources used:", result["sources"])

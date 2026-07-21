"""
scripts/news_agent.py

News Agent: fetches today's financial headlines from NewsAPI,
stores real article text (not AI-generated) into embedded_content
so the Learning Agent's RAG store stays current with real market news.

Run manually:
    python -m scripts.news_agent

Or schedule via Windows Task Scheduler to run daily at 8 AM.

Design choice: we store actual source text (headline + description + URL),
not AI-generated summaries. This keeps the knowledge base factually
accurate and defensible. The Learning Agent handles explanation on demand.
"""

import os
import uuid
import requests
from datetime import datetime, timezone
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import engine
from app.models import EmbeddedContent

load_dotenv()

NEWS_API_KEY = os.environ["NEWS_API_KEY"]
NEWS_API_URL = "https://newsapi.org/v2/everything"

# Topics to fetch -- matched to your embedded_content tags
SEARCH_QUERIES = [
    "stock market investing",
    "index funds ETF",
    "market volatility",
    "personal finance investing",
    "stock market beginners",
]

# Map query keywords to tags stored in embedded_content
QUERY_TAG_MAP = {
    "stock market investing": ["stocks", "investing", "markets"],
    "index funds ETF": ["index-funds", "etf", "passive-investing"],
    "market volatility": ["volatility", "risk", "markets"],
    "personal finance investing": ["personal-finance", "investing", "savings"],
    "stock market beginners": ["beginner", "stocks", "investing"],
}


def fetch_articles(query: str, page_size: int = 5) -> list[dict]:
    """
    Fetches top articles for a given query from NewsAPI.
    Returns list of article dicts.
    """
    params = {
        "q": query,
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": page_size,
        "apiKey": NEWS_API_KEY,
    }
    response = requests.get(NEWS_API_URL, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()
    return data.get("articles", [])


def article_exists(title: str, conn) -> bool:
    """
    Checks if an article with this title already exists in embedded_content.
    Prevents duplicate ingestion on repeated runs.
    """
    result = conn.execute(
        text("SELECT 1 FROM embedded_content WHERE title = :title LIMIT 1"),
        {"title": title},
    ).fetchone()
    return result is not None


def embed_text(text_to_embed: str) -> list[float]:
    """
    Embeds text using Gemini -- same embedding model as Learning Agent
    so vectors are comparable in pgvector search.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    result = client.models.embed_content(
        model="gemini-embedding-001",
        contents=text_to_embed,
        config=types.EmbedContentConfig(
            task_type="RETRIEVAL_DOCUMENT",
            output_dimensionality=1536,
        ),
    )
    return result.embeddings[0].values


def build_content(article: dict) -> str:
    """
    Builds the content string to store and embed.
    Uses real article text -- description + source name + URL.
    No AI generation involved.
    """
    description = article.get("description") or article.get("title", "")
    source_name = article.get("source", {}).get("name", "Unknown source")
    url = article.get("url", "")

    # Clean up description -- some have [+N chars] truncation markers
    if "[+" in description:
        description = description.split("[+")[0].strip()

    return f"{description} (Source: {source_name}. Read more: {url})"


def run():
    """
    Main News Agent pipeline:
    1. Fetch articles for each topic
    2. Deduplicate against existing content
    3. Embed and store new articles
    """
    print(f"News Agent starting at {datetime.now(timezone.utc).isoformat()}")

    inserted = 0
    skipped = 0
    errors = 0

    with engine.connect() as conn:
        for query in SEARCH_QUERIES:
            print(f"\nFetching: '{query}'")
            try:
                articles = fetch_articles(query, page_size=5)
            except Exception as e:
                print(f"  ERROR fetching articles: {e}")
                errors += 1
                continue

            tags = QUERY_TAG_MAP.get(query, ["news", "finance"])

            for article in articles:
                title = article.get("title", "").strip()

                # Skip articles with no useful title or content
                if not title or title == "[Removed]":
                    skipped += 1
                    continue

                # Deduplication check
                if article_exists(title, conn):
                    print(f"  SKIP (exists): {title[:60]}")
                    skipped += 1
                    continue

                content = build_content(article)
                if not content.strip():
                    skipped += 1
                    continue

                try:
                    # Embed the content
                    embedding = embed_text(content)
                    embedding_literal = (
                        "[" + ",".join(str(v) for v in embedding) + "]"
                    )

                    # Insert into embedded_content
                    conn.execute(
                        text("""
                            INSERT INTO embedded_content
                                (id, source, title, content, embedding, tags,
                                 difficulty, created_at)
                            VALUES
                                (:id, :source, :title, :content,
                                 CAST(:embedding AS vector), :tags,
                                 :difficulty, :created_at)
                        """),
                        {
                            "id": str(uuid.uuid4()),
                            "source": "news",
                            "title": title,
                            "content": content,
                            "embedding": embedding_literal,
                            "tags": tags,
                            "difficulty": "easy",
                            "created_at": datetime.now(timezone.utc),
                        },
                    )
                    conn.commit()
                    print(f"  STORED: {title[:60]}")
                    inserted += 1

                except Exception as e:
                    print(f"  ERROR storing '{title[:60]}': {e}")
                    errors += 1

    print(f"\nDone. Inserted: {inserted}, Skipped: {skipped}, Errors: {errors}")


if __name__ == "__main__":
    run()
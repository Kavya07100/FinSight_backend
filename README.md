# FinSight Backend

FinSight is a virtual investing and financial-literacy platform. It lets users complete a
risk-profile onboarding flow, get an AI-generated personalized learning path, practice trading
with simulated (paper) money against real historical price data, track a virtual portfolio, and
ask a RAG-backed chat assistant questions about investing basics.

This repository is the FastAPI backend: it owns the Postgres schema, the risk-scoring engine, the
backtest/simulation engine, the portfolio/transactions ledger, and the two LLM-backed features
(the Learning Agent's RAG chat and the Strategy Agent's learning-path generator).

## Tech Stack

- **FastAPI** — HTTP API layer
- **PostgreSQL** — primary datastore (users, risk profiles, strategies, simulations, portfolio,
  transactions, price history)
- **pgvector** — Postgres extension used for similarity search over embedded educational content
  (the Learning Agent's RAG retrieval step)
- **SQLAlchemy** — ORM / query layer
- **Groq** (`llama-3.3-70b-versatile`) — text generation for the Learning Agent's RAG answers and
  the Strategy Agent's learning-path generation
- **Google Gemini** (`gemini-embedding-001`) — embeddings only (both for indexing educational
  content and for embedding user questions at query time)
- **yfinance** — free historical OHLCV price data (Yahoo Finance), used to seed `price_history`

## Prerequisites

- Python 3.11+
- PostgreSQL (a local instance is fine)
- API keys:
  - **GEMINI_API_KEY** — [Google AI Studio](https://aistudio.google.com/)
  - **GROQ_API_KEY** — [Groq Console](https://console.groq.com/)
  - **NEWS_API_KEY** — [newsapi.org](https://newsapi.org/) (used by `scripts/news_agent.py`)

## Setup

```bash
# 1. Clone and enter the project
git clone <repo-url> finsight_backend
cd finsight_backend

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
# Create a .env file in the project root (see "Environment Variables" below)

# 5. Create the database and apply the schema
createdb finsight
psql -d finsight -f schema.sql

# 5a. Enable pgvector and add the embedding column (needed for the Learning Agent's
#     RAG store; schema.sql intentionally skips this since it's optional until you
#     use the chat feature)
psql -d finsight -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -d finsight -c "ALTER TABLE embedded_content ADD COLUMN embedding vector(1536);"

# 6. Seed historical price data (takes a minute or two)
python -m scripts.ingest_prices

# 6a. (Optional, for the /learning/ask chat endpoint) Embed the educational content
python -m scripts.embed_content

# 7. Run the API server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`. Interactive docs (Swagger UI) are at
`http://localhost:8000/docs`.

By default, CORS is configured to allow requests from `http://localhost:3000` (the frontend's dev
server) — adjust `allow_origins` in `app/main.py` if your frontend runs elsewhere.

## Environment Variables

Create a `.env` file in the project root:

```bash
DATABASE_URL=postgresql://user:password@localhost:5432/finsight
GEMINI_API_KEY=your_gemini_api_key
GROQ_API_KEY=your_groq_api_key
NEWS_API_KEY=your_newsapi_key
```

| Variable | Required for | Description |
|---|---|---|
| `DATABASE_URL` | Everything | Postgres connection string |
| `GEMINI_API_KEY` | `/learning/ask`, `scripts/embed_content.py` | Embeddings for RAG retrieval |
| `GROQ_API_KEY` | `/learning/ask`, `/users/{id}/strategy` | LLM text generation |
| `NEWS_API_KEY` | `scripts/news_agent.py` | Market news ingestion (standalone script, not a live endpoint) |

## API Endpoints

All endpoints return JSON. `{user_id}` is a UUID.

### Users
| Method | Path | Description |
|---|---|---|
| POST | `/users` | Create a user from onboarding data (full name, age, monthly income, current savings) |
| GET | `/users/{user_id}` | Get a user's profile |
| PUT | `/users/{user_id}` | Update a user's profile; if `investment_goal` or `risk_tolerance` is included, also recomputes and stores a new risk-profile version |

### Portfolio Service (risk scoring)
| Method | Path | Description |
|---|---|---|
| POST | `/users/{user_id}/risk-profile` | Compute and store a new (versioned) risk profile from income/savings/goal/risk-tolerance |
| GET | `/users/{user_id}/risk-profile` | Get the latest risk profile |
| GET | `/users/{user_id}/risk-profile/history` | Get all risk-profile versions, oldest first |

### Simulation Environment (sandbox backtesting)
| Method | Path | Description |
|---|---|---|
| POST | `/users/{user_id}/simulate/sandbox` | Run a backtest over a list of buy/sell trades against real historical prices, compare against a benchmark ticker (default SPY), and record resulting transactions/holdings |
| POST | `/users/{user_id}/simulate/{log_id}/analyze` | Run the Behavior Engine over a completed simulation log (panic-sell rate, trade frequency, diversification, LLM feedback) |

### Portfolio Engine
| Method | Path | Description |
|---|---|---|
| GET | `/users/{user_id}/portfolio` | Current holdings marked to market, total value, total invested, overall return %, today's P&L |
| GET | `/users/{user_id}/transactions` | Last 10 transactions, newest first |
| GET | `/users/{user_id}/simulations/latest` | Most recent simulation log (metrics + daily portfolio values) |

### Learning Agent (RAG chat)
| Method | Path | Description |
|---|---|---|
| POST | `/learning/ask` | Answer a free-text question, grounded in retrieved educational content, with cited sources |

### Strategy Agent
| Method | Path | Description |
|---|---|---|
| POST | `/users/{user_id}/strategy` | Generate and store a new (versioned) personalized learning path from the user's latest risk profile and behavior score |
| GET | `/users/{user_id}/strategy` | Get the latest learning path |

## Project Structure

```
app/
  main.py               FastAPI app + all routes
  models.py              SQLAlchemy models
  schemas.py              Pydantic request/response schemas
  database.py             Engine/session setup
  portfolio_service.py     Rules-based risk scoring
  backtest_engine.py        Pure backtest simulation logic
  price_data.py              price_history query layer
  learning_agent.py            RAG pipeline (Gemini embeddings + Groq generation)
  strategy_agent.py              Learning-path generation
  behavior_engine.py               Trading-behavior analysis
scripts/
  ingest_prices.py        Pulls OHLCV data from yfinance into price_history
  embed_content.py          Embeds educational content into embedded_content
  literacy_content.py         Source educational passages
  news_agent.py                 Standalone market-news ingestion (needs NEWS_API_KEY)
schema.sql               Full Postgres schema (source of truth for table shapes)
```

-- FinSight: Backend Foundations Schema
-- Phase 1: users, price history, risk profiles, strategy configs,
-- simulation logs, embedded content (for later RAG)

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
-- CREATE EXTENSION IF NOT EXISTS vector;  -- pgvector: only needed once you build
-- the Learning Agent / RAG. Skip installing it for Phase 1. When you do need it,
-- uncomment this line AND the "embedding VECTOR(1536)" column below.

-- ============================================================
-- USERS
-- ============================================================
-- Kept deliberately thin. Auth fields + identity only.
-- Everything derived (risk profile, strategy, behavior) lives in
-- its own table, NOT as columns here. Reason: those things change
-- over time and you need history, not just "current value."
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           TEXT UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name       TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- RISK PROFILES (Portfolio Service output)
-- ============================================================
-- Versioned, not a single row per user. Why: the Behavior Engine
-- loop can eventually trigger a re-score (e.g. user's situation
-- changes, or you let them redo onboarding). If this were one row
-- per user with UPDATE, you'd lose the ability to show "how did my
-- risk profile change" or to debug which profile a given strategy
-- was built from. Cheap now, expensive to retrofit later.
CREATE TABLE risk_profiles (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version                 INT NOT NULL,

    -- raw inputs, stored alongside the output on purpose:
    -- if you tweak the scoring formula later, you can re-run it
    -- against historical inputs and compare, instead of the inputs
    -- being lost forever after scoring.
    income                  NUMERIC(14,2) NOT NULL,
    savings                 NUMERIC(14,2) NOT NULL,
    goal                    TEXT NOT NULL,
    time_horizon_years      NUMERIC(5,2) NOT NULL,
    pct_income_investable   NUMERIC(5,2) NOT NULL,   -- 0-100
    risk_tolerance_input    INT NOT NULL,             -- 1-5 self-reported

    -- computed output
    risk_score              INT NOT NULL,             -- 0-100
    category                TEXT NOT NULL,             -- conservative / moderate / moderate-aggressive / aggressive
    score_breakdown         JSONB NOT NULL,             -- component-level scores, for auditability/debugging

    computed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, version)
);

CREATE INDEX idx_risk_profiles_user_latest ON risk_profiles (user_id, version DESC);

-- ============================================================
-- PRICE HISTORY (shared data store)
-- ============================================================
-- One big flat table, not split per-ticker. Standard OHLCV shape.
-- UNIQUE(ticker, date) does double duty: prevents duplicate
-- ingestion AND gives you a natural upsert key when re-running
-- a data pull.
CREATE TABLE price_history (
    id          BIGSERIAL PRIMARY KEY,
    ticker      TEXT NOT NULL,
    date        DATE NOT NULL,
    open        NUMERIC(14,4) NOT NULL,
    high        NUMERIC(14,4) NOT NULL,
    low         NUMERIC(14,4) NOT NULL,
    close       NUMERIC(14,4) NOT NULL,
    volume      BIGINT NOT NULL,

    UNIQUE (ticker, date)
);

-- The Simulation Environment's main query pattern will be:
-- "give me all rows for ticker X between date A and B, in order."
-- This index makes that a range scan instead of a full table scan.
CREATE INDEX idx_price_history_ticker_date ON price_history (ticker, date);

-- ============================================================
-- STRATEGY CONFIGS (Strategy Agent output)
-- ============================================================
-- Versioned for the same loop reason as risk_profiles: the doc's
-- diagram literally shows Strategy Agent producing v1, then
-- getting called again after Behavior Engine feedback to produce
-- v2. You need both rows to exist simultaneously.
CREATE TABLE strategy_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version         INT NOT NULL,
    risk_profile_id UUID NOT NULL REFERENCES risk_profiles(id),

    -- JSONB, not normalized module/step tables. This is a
    -- deliberate tradeoff: the "path" shape is exactly what the
    -- Strategy Agent (LLM) emits and what the Simulation
    -- Environment consumes directly -- no translation layer needed.
    -- Cost: you can't easily SQL-query "all users on module X"
    -- without a JSONB query. For a capstone's scope, that query
    -- doesn't matter; if it did later, you'd normalize this into
    -- a strategy_modules table.
    path            JSONB NOT NULL,

    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),

    UNIQUE (user_id, version)
);

CREATE INDEX idx_strategy_configs_user_latest ON strategy_configs (user_id, version DESC);

-- ============================================================
-- SIMULATION LOGS (Simulation Environment output -> Behavior Engine input)
-- ============================================================
CREATE TABLE simulation_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    strategy_config_id  UUID REFERENCES strategy_configs(id),  -- nullable: sandbox sessions may not follow a strategy

    mode                TEXT NOT NULL CHECK (mode IN ('fixed', 'sandbox')),

    -- Same JSONB tradeoff as strategy_configs.path: trades are a
    -- sequence of {ticker, action, quantity, timestamp} events.
    -- Normalizing into a trades table is the "more correct" DB
    -- design, but the Behavior Engine reads the whole sequence at
    -- once per session anyway (never queries individual trades
    -- across sessions), so JSONB avoids a join for no benefit here.
    trades              JSONB NOT NULL DEFAULT '[]',

    -- filled in later by the Behavior Engine, not at insert time.
    -- Nullable until that analysis runs.
    metrics             JSONB,

    started_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at            TIMESTAMPTZ
);

CREATE INDEX idx_simulation_logs_user ON simulation_logs (user_id, started_at DESC);

-- ============================================================
-- EMBEDDED CONTENT (for Learning Agent's RAG store)
-- ============================================================
-- Not used by Portfolio Service, but the doc asks for this table
-- now so ingestion can start independently of the Learning Agent
-- being built. embedding dimension (1536) matches common
-- embedding models (e.g. OpenAI text-embedding-3-small); adjust
-- if you pick a different embedding model.
CREATE TABLE embedded_content (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source      TEXT NOT NULL,       -- 'news', 'educational', etc.
    title       TEXT,
    content     TEXT NOT NULL,
    -- embedding   VECTOR(1536),  -- uncomment once pgvector is installed
    tags        TEXT[] DEFAULT '{}',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ivfflat index for approximate nearest-neighbor search.
-- Only build this after you have real data loaded (needs rows to
-- train on) -- fine to run this line later, not required for Phase 1.
-- CREATE INDEX idx_embedded_content_embedding ON embedded_content
--     USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

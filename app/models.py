import uuid
from sqlalchemy import (
    Column, String, Text, Numeric, Integer, BigInteger, Date,
    TIMESTAMP, ForeignKey, UniqueConstraint, CheckConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(Text, unique=True, nullable=False)
    hashed_password = Column(Text, nullable=False)
    full_name = Column(Text)
    age = Column(Integer)
    monthly_income = Column(Numeric(12, 2))
    current_savings = Column(Numeric(14, 2))
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    risk_profiles = relationship("RiskProfile", back_populates="user")


class RiskProfile(Base):
    __tablename__ = "risk_profiles"
    __table_args__ = (UniqueConstraint("user_id", "version"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)

    income = Column(Numeric(14, 2), nullable=False)
    savings = Column(Numeric(14, 2), nullable=False)
    goal = Column(Text, nullable=False)
    time_horizon_years = Column(Numeric(5, 2), nullable=False)
    pct_income_investable = Column(Numeric(5, 2), nullable=False)
    risk_tolerance_input = Column(Integer, nullable=False)

    risk_score = Column(Integer, nullable=False)
    category = Column(Text, nullable=False)
    score_breakdown = Column(JSONB, nullable=False)

    computed_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="risk_profiles")


class PriceHistory(Base):
    __tablename__ = "price_history"
    __table_args__ = (UniqueConstraint("ticker", "date"),)

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    ticker = Column(Text, nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Numeric(14, 4), nullable=False)
    high = Column(Numeric(14, 4), nullable=False)
    low = Column(Numeric(14, 4), nullable=False)
    close = Column(Numeric(14, 4), nullable=False)
    volume = Column(BigInteger, nullable=False)


class StrategyConfig(Base):
    __tablename__ = "strategy_configs"
    __table_args__ = (UniqueConstraint("user_id", "version"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    version = Column(Integer, nullable=False)
    risk_profile_id = Column(UUID(as_uuid=True), ForeignKey("risk_profiles.id"), nullable=False)
    path = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class SimulationLog(Base):
    __tablename__ = "simulation_logs"
    __table_args__ = (CheckConstraint("mode IN ('fixed', 'sandbox')"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    strategy_config_id = Column(UUID(as_uuid=True), ForeignKey("strategy_configs.id"), nullable=True)
    mode = Column(Text, nullable=False)
    trades = Column(JSONB, nullable=False, default=list)
    metrics = Column(JSONB, nullable=True)
    started_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)


class PortfolioHolding(Base):
    __tablename__ = "portfolio_holdings"
    __table_args__ = (UniqueConstraint("user_id", "ticker"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(Text, nullable=False)
    company_name = Column(Text)
    quantity = Column(Integer, nullable=False)
    avg_buy_price = Column(Numeric(14, 4), nullable=False)


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (CheckConstraint("action IN ('buy', 'sell')"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(Text, nullable=False)
    company_name = Column(Text)
    action = Column(Text, nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Numeric(14, 4), nullable=False)
    total_value = Column(Numeric(14, 2), nullable=False)
    trade_date = Column(Date, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())


class EmbeddedContent(Base):
    __tablename__ = "embedded_content"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source = Column(Text, nullable=False)
    title = Column(Text)
    content = Column(Text, nullable=False)
    # embedding column omitted here deliberately -- add via pgvector's
    # SQLAlchemy type (from pgvector.sqlalchemy import Vector) once you
    # actually build the Learning Agent. Not needed for Phase 1.
    tags = Column(ARRAY(Text), default=list)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

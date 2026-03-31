from datetime import datetime
from sqlalchemy.ext.asyncio import (
    create_async_engine, AsyncSession, async_sessionmaker
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import String, Text, DateTime, Boolean, ForeignKey, JSON, func
from core.config import get_settings
import uuid

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.environment == "development",
    pool_size=10,
    max_overflow=20,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=True)
    tier: Mapped[str] = mapped_column(String(50), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    reports: Mapped[list["Report"]] = relationship("Report", back_populates="user")
    watchlist: Mapped[list["Watchlist"]] = relationship("Watchlist", back_populates="user")


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50))
    asset_symbol: Mapped[str] = mapped_column(String(50))
    analysis_type: Mapped[str] = mapped_column(String(50))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    celery_task_id: Mapped[str] = mapped_column(String, nullable=True)
    error_message: Mapped[str] = mapped_column(Text, nullable=True)
    file_url: Mapped[str] = mapped_column(String, nullable=True)
    file_size_kb: Mapped[int] = mapped_column(nullable=True)
    report_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="reports")


class Watchlist(Base):
    __tablename__ = "watchlists"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"), nullable=False)
    asset_symbol: Mapped[str] = mapped_column(String(50), nullable=False)
    asset_type: Mapped[str] = mapped_column(String(50), nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    user: Mapped["User"] = relationship("User", back_populates="watchlist")


class CachedData(Base):
    __tablename__ = "cached_data"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4())
    )
    cache_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    data: Mapped[dict] = mapped_column(JSON, nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    ttl_minutes: Mapped[int] = mapped_column(default=15)
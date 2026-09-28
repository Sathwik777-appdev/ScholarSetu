from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from app.config import settings

_engine_kwargs = {"echo": settings.SQL_ECHO}
if settings.DATABASE_NULL_POOL:
    _engine_kwargs["poolclass"] = NullPool
else:
    # Small databases (e.g. Cloud SQL db-f1-micro) allow few connections: size the pool per instance.
    _engine_kwargs.update(pool_size=settings.DATABASE_POOL_SIZE, max_overflow=settings.DATABASE_MAX_OVERFLOW,
                          pool_pre_ping=True, pool_recycle=1800)

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)
AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

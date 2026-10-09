"""
Database Engine & Session Management
Configures SQLAlchemy 2.0 engine, connection pooling, and SQLite WAL pragma.
"""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

# Engine configuration
connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, echo=settings.DB_ECHO, pool_pre_ping=True)


# Apply SQLite WAL and busy timeout pragmas for high concurrency
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    if settings.DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request
    and guarantees proper closure/cleanup upon completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

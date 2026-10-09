"""
FastAPI Dependencies
Provides dependency-injected database sessions and utility dependencies.
"""

from app.db.session import get_db

# Re-export get_db for convenient dependency injection
__all__ = ["get_db"]

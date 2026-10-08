"""SQLAlchemy session factory for the MCP server (separate from FastAPI's session)."""

from sqlalchemy.orm import sessionmaker

from app.db.session import engine

McpSession = sessionmaker(bind=engine, expire_on_commit=False)


def get_session():
    return McpSession()

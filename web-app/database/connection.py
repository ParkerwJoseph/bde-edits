from sqlmodel import SQLModel, create_engine, Session
from config.settings import DATABASE_URL

# ---------------------------------------------------------------------
# Database Engine Configuration
# ---------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    echo=False,           # Set to True for SQL query debugging
    pool_size=10,         # Max number of DB connections in pool
    max_overflow=5,       # Allow 5 extra connections during peak load
    pool_recycle=300,     # Recycle connections every 5 min
    pool_pre_ping=True,   # Verify connection health before use
    pool_timeout=60       # Wait up to 60 seconds for a connection
)


# ---------------------------------------------------------------------
# Database Initialization
# ---------------------------------------------------------------------
def create_db_and_tables():
    """
    Create all database tables defined in SQLModel models.
    Should be called once at app startup (e.g., in main.py).
    """
    SQLModel.metadata.create_all(engine)


# ---------------------------------------------------------------------
# Dependency for FastAPI Routes (context-managed)
# ---------------------------------------------------------------------
def get_session():
    """
    Dependency for FastAPI endpoints — provides a scoped SQLModel session.
    Example:
        @router.get("/users")
        def get_users(session: Session = Depends(get_session)):
            ...
    """
    with Session(engine) as session:
        yield session


# ---------------------------------------------------------------------
# Optional: Direct Session for Scripts / Sync Operations
# ---------------------------------------------------------------------
def get_db_session() -> Session:
    """
    For non-FastAPI contexts (like scripts, CLI, or background tasks).
    Returns a raw Session you must close manually.
    Example:
        session = get_db_session()
        ...
        session.close()
    """
    return Session(engine)

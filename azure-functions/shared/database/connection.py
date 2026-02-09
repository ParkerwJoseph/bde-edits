import time
from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy import event
from shared.config.settings import DATABASE_URL
from shared.utils.logger import get_logger

logger = get_logger(__name__)

# Lazy initialization of database engine
_engine = None
_event_listeners_registered = False


def get_engine():
    """Get or create the database engine with lazy initialization."""
    global _engine, _event_listeners_registered

    if _engine is None:
        if not DATABASE_URL:
            raise ValueError("DATABASE_URL environment variable is not set")

        logger.info(f"[DB] Initializing database engine...")
        _engine = create_engine(
            DATABASE_URL,
            echo=False,
            pool_size=5,
            max_overflow=3,
            pool_recycle=300,
            pool_pre_ping=True,
            pool_timeout=60
        )
        logger.info(f"[DB] Database engine created successfully")

        # Register event listeners only once
        if not _event_listeners_registered:
            _register_event_listeners(_engine)
            _event_listeners_registered = True

    return _engine


def _register_event_listeners(eng):
    """Register connection pool event listeners."""

    @event.listens_for(eng.pool, "checkout")
    def on_checkout(dbapi_conn, connection_record, connection_proxy):
        """Log when a connection is checked out from the pool."""
        try:
            logger.debug(f"[DB Pool] Connection checked out (pool size: {eng.pool.size()}, "
                        f"checked out: {eng.pool.checkedout()}, overflow: {eng.pool.overflow()})")
        except Exception:
            pass  # Don't fail on logging errors

    @event.listens_for(eng.pool, "checkin")
    def on_checkin(dbapi_conn, connection_record):
        """Log when a connection is returned to the pool."""
        try:
            logger.debug(f"[DB Pool] Connection checked in (pool size: {eng.pool.size()}, "
                        f"checked out: {eng.pool.checkedout()}, overflow: {eng.pool.overflow()})")
        except Exception:
            pass  # Don't fail on logging errors

    @event.listens_for(eng, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Track query execution start time."""
        try:
            conn.info.setdefault('query_start_time', []).append(time.time())
        except Exception:
            pass

    @event.listens_for(eng, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        """Log slow queries."""
        try:
            query_times = conn.info.get('query_start_time', [])
            if query_times:
                total = time.time() - query_times.pop()
                if total > 5.0:  # Log queries taking more than 5 seconds
                    logger.warning(f"[DB] Slow query detected ({total:.2f}s): {statement[:100]}...")
        except Exception:
            pass  # Don't fail on logging errors


# Backward compatibility - module-level engine variable
# Code that imports 'engine' directly will get None initially,
# but get_engine() should be used instead
engine = None


def get_db_session() -> Session:
    """
    Get a database session for Azure Function context.
    Returns a raw Session you must close manually.
    """
    start_time = time.time()
    try:
        eng = get_engine()

        # Log pool status before acquiring
        logger.info(f"[DB Pool] Acquiring session (pool: size={eng.pool.size()}, "
                   f"checked_out={eng.pool.checkedout()}, overflow={eng.pool.overflow()})")

        session = Session(eng)
        elapsed = time.time() - start_time

        if elapsed > 1.0:  # Log if getting session took more than 1 second (pool contention)
            logger.warning(f"[DB Pool] Session acquisition took {elapsed:.2f}s - possible pool contention "
                          f"(checked out: {eng.pool.checkedout()}, overflow: {eng.pool.overflow()})")
        else:
            logger.info(f"[DB Pool] Session acquired in {elapsed:.2f}s")

        return session
    except Exception as e:
        elapsed = time.time() - start_time
        logger.error(f"[DB Pool] Failed to get session after {elapsed:.2f}s: {type(e).__name__}: {e}")
        import traceback
        logger.error(f"[DB Pool] Traceback: {traceback.format_exc()}")
        raise


def get_pool_status() -> dict:
    """
    Get current database connection pool status.

    Returns:
        Dictionary with pool status information
    """
    eng = get_engine()
    return {
        "pool_size": eng.pool.size(),
        "checked_out": eng.pool.checkedout(),
        "overflow": eng.pool.overflow(),
        "checked_in": eng.pool.checkedin(),
    }

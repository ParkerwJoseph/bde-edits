import json
from datetime import datetime
from typing import Optional, List
from sqlmodel import Session, select, col

from database.models.chat import ChatSession, ChatMessageModel, MessageRole


def create_session(
    session: Session,
    tenant_id: str,
    user_id: str,
    title: str = "New Chat",
    company_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None
) -> ChatSession:
    """Create a new chat session."""
    chat_session = ChatSession(
        tenant_id=tenant_id,
        user_id=user_id,
        title=title,
        company_id=company_id,
        document_ids_json=json.dumps(document_ids) if document_ids else None,
    )
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def get_session(session: Session, session_id: str, tenant_id: str) -> Optional[ChatSession]:
    """Get a chat session by ID, scoped to tenant."""
    return session.exec(
        select(ChatSession)
        .where(ChatSession.id == session_id)
        .where(ChatSession.tenant_id == tenant_id)
    ).first()


def get_user_sessions(
    session: Session,
    tenant_id: str,
    user_id: str,
    company_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50
) -> List[ChatSession]:
    """Get all chat sessions for a user within a tenant, optionally filtered by company."""
    query = (
        select(ChatSession)
        .where(ChatSession.tenant_id == tenant_id)
        .where(ChatSession.user_id == user_id)
    )
    if company_id:
        query = query.where(ChatSession.company_id == company_id)
    query = query.order_by(col(ChatSession.updated_at).desc()).offset(skip).limit(limit)
    return list(session.exec(query).all())


def update_session(
    session: Session,
    chat_session: ChatSession,
    title: Optional[str] = None,
    document_ids: Optional[List[str]] = None
) -> ChatSession:
    """Update a chat session."""
    if title is not None:
        chat_session.title = title
    if document_ids is not None:
        chat_session.document_ids_json = json.dumps(document_ids) if document_ids else None
    chat_session.updated_at = datetime.utcnow()
    session.add(chat_session)
    session.commit()
    session.refresh(chat_session)
    return chat_session


def delete_session(session: Session, chat_session: ChatSession) -> None:
    """Delete a chat session and all its messages."""
    # Delete all messages first
    messages = session.exec(
        select(ChatMessageModel).where(ChatMessageModel.session_id == chat_session.id)
    ).all()
    for msg in messages:
        session.delete(msg)

    # Delete the session
    session.delete(chat_session)
    session.commit()


def add_message(
    session: Session,
    session_id: str,
    tenant_id: str,
    role: MessageRole,
    content: str,
    sources: Optional[List[dict]] = None,
    usage_stats: Optional[dict] = None
) -> ChatMessageModel:
    """Add a message to a chat session."""
    message = ChatMessageModel(
        session_id=session_id,
        tenant_id=tenant_id,
        role=role,
        content=content,
        sources_json=json.dumps(sources) if sources else None,
        usage_stats_json=json.dumps(usage_stats) if usage_stats else None,
    )
    session.add(message)

    # Update session's updated_at
    chat_session = session.get(ChatSession, session_id)
    if chat_session:
        chat_session.updated_at = datetime.utcnow()
        session.add(chat_session)

    session.commit()
    session.refresh(message)
    return message


def get_session_messages(
    session: Session,
    session_id: str,
    tenant_id: str,
    limit: int = 100
) -> List[ChatMessageModel]:
    """Get all messages in a chat session."""
    return list(session.exec(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_id)
        .where(ChatMessageModel.tenant_id == tenant_id)
        .order_by(col(ChatMessageModel.created_at).asc())
        .limit(limit)
    ).all())


def get_conversation_history(
    session: Session,
    session_id: str,
    tenant_id: str,
    limit: int = 6
) -> List[dict]:
    """
    Get conversation history in the format expected by RAG service.

    Default limit is 6 messages (3 exchanges) which provides enough context
    for query rewriting while keeping token usage manageable.
    """
    messages = session.exec(
        select(ChatMessageModel)
        .where(ChatMessageModel.session_id == session_id)
        .where(ChatMessageModel.tenant_id == tenant_id)
        .order_by(col(ChatMessageModel.created_at).desc())
        .limit(limit)
    ).all()

    # Reverse to get chronological order and format for RAG
    return [
        {"role": msg.role.value, "content": msg.content}
        for msg in reversed(messages)
    ]


def generate_session_title(first_message: str) -> str:
    """Generate a title from the first message."""
    # Take first 50 characters of the message
    title = first_message[:50].strip()
    if len(first_message) > 50:
        title += "..."
    return title or "New Chat"

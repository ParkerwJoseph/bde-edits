import json
import asyncio
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlmodel import Session, select

from database.connection import get_session
from database.models import User
from database.models.document import Document, BDEPillar, PILLAR_DESCRIPTIONS
from database.models.connector import ConnectorConfig
from database.models.chat import ChatSession, ChatMessageModel, MessageRole
from az_auth.dependencies import require_permission
from az_auth.token import decode_token
from az_auth.service import get_user_by_azure_id
from core.permissions import Permissions
from database.connection import engine
from services.rag_service import get_rag_service
from api.chat import crud as chat_crud
from api.chat.schemas import (
    ChatRequest, ChatResponse,
    SearchRequest, SearchResponse,
    SourceInfo, ChunkInfo,
    ChatSessionCreate, ChatSessionUpdate,
    ChatSessionResponse, ChatSessionDetailResponse, ChatSessionListResponse,
    ChatMessageResponse,
)
from api.chat.websocket_manager import chat_ws_manager
from utils.logger import get_logger


def get_pillar_label(pillar: str) -> str:
    """Convert pillar value to human-readable label."""
    pillar_labels = {
        "financial_health": "Financial Health",
        "gtm_engine": "GTM Engine",
        "customer_health": "Customer Health",
        "product_technical": "Product & Technical",
        "operational_maturity": "Operational Maturity",
        "leadership_transition": "Leadership Transition",
        "ecosystem_dependency": "Ecosystem Dependency",
        "service_software_ratio": "Service/Software Ratio",
        "general": "General",
    }
    return pillar_labels.get(pillar, pillar.replace("_", " ").title())


logger = get_logger(__name__)

router = APIRouter()


# =============================================================================
# Chat Session Endpoints
# =============================================================================

@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    company_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """List all chat sessions for the current user, optionally filtered by company."""
    sessions = chat_crud.get_user_sessions(
        session=session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        company_id=company_id,
        skip=skip,
        limit=limit
    )

    session_responses = [
        ChatSessionResponse(
            id=s.id,
            title=s.title,
            company_id=s.company_id,
            document_ids=json.loads(s.document_ids_json) if s.document_ids_json else None,
            created_at=s.created_at,
            updated_at=s.updated_at
        )
        for s in sessions
    ]

    return ChatSessionListResponse(
        sessions=session_responses,
        total=len(session_responses)
    )


@router.post("/sessions", response_model=ChatSessionResponse)
async def create_session(
    request: ChatSessionCreate,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Create a new chat session."""
    chat_session = chat_crud.create_session(
        session=session,
        tenant_id=user.tenant_id,
        user_id=user.id,
        title=request.title or "New Chat",
        company_id=request.company_id,
        document_ids=request.document_ids
    )

    return ChatSessionResponse(
        id=chat_session.id,
        title=chat_session.title,
        company_id=chat_session.company_id,
        document_ids=json.loads(chat_session.document_ids_json) if chat_session.document_ids_json else None,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at
    )


@router.get("/sessions/{session_id}", response_model=ChatSessionDetailResponse)
async def get_session_with_messages(
    session_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Get a chat session with all its messages."""
    chat_session = chat_crud.get_session(
        session=session,
        session_id=session_id,
        tenant_id=user.tenant_id
    )

    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    # Check user owns this session
    if chat_session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    messages = chat_crud.get_session_messages(
        session=session,
        session_id=session_id,
        tenant_id=user.tenant_id
    )

    message_responses = [
        ChatMessageResponse(
            id=m.id,
            role=m.role.value,
            content=m.content,
            sources=json.loads(m.sources_json) if m.sources_json else None,
            usage_stats=json.loads(m.usage_stats_json) if m.usage_stats_json else None,
            created_at=m.created_at
        )
        for m in messages
    ]

    return ChatSessionDetailResponse(
        id=chat_session.id,
        title=chat_session.title,
        company_id=chat_session.company_id,
        document_ids=json.loads(chat_session.document_ids_json) if chat_session.document_ids_json else None,
        messages=message_responses,
        created_at=chat_session.created_at,
        updated_at=chat_session.updated_at
    )


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: str,
    request: ChatSessionUpdate,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Update a chat session."""
    chat_session = chat_crud.get_session(
        session=session,
        session_id=session_id,
        tenant_id=user.tenant_id
    )

    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if chat_session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    updated_session = chat_crud.update_session(
        session=session,
        chat_session=chat_session,
        title=request.title,
        document_ids=request.document_ids
    )

    return ChatSessionResponse(
        id=updated_session.id,
        title=updated_session.title,
        company_id=updated_session.company_id,
        document_ids=json.loads(updated_session.document_ids_json) if updated_session.document_ids_json else None,
        created_at=updated_session.created_at,
        updated_at=updated_session.updated_at
    )


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """Delete a chat session and all its messages."""
    chat_session = chat_crud.get_session(
        session=session,
        session_id=session_id,
        tenant_id=user.tenant_id
    )

    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")

    if chat_session.user_id != user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    chat_crud.delete_session(session=session, chat_session=chat_session)

    return {"message": "Chat session deleted"}


# =============================================================================
# Chat Endpoints
# =============================================================================

@router.post("/chat", response_model=ChatResponse)
async def chat_with_documents(
    request: ChatRequest,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """
    Chat with documents using RAG.
    Retrieves relevant chunks and generates an AI answer.
    Messages are persisted in a chat session.
    """
    logger.info(f"[Chat] Query: {request.query[:100]}...")
    logger.info(f"[Chat] Company ID: {request.company_id}")
    logger.info(f"[Chat] Document IDs: {request.document_ids}")
    logger.info(f"[Chat] Session ID: {request.session_id}")

    try:
        rag_service = get_rag_service()

        # Get or create session
        chat_session = None
        company_id = request.company_id
        if request.session_id:
            chat_session = chat_crud.get_session(
                session=session,
                session_id=request.session_id,
                tenant_id=user.tenant_id
            )
            if not chat_session:
                raise HTTPException(status_code=404, detail="Chat session not found")
            if chat_session.user_id != user.id:
                raise HTTPException(status_code=403, detail="Access denied")
            # Use session's company_id if not provided in request
            if not company_id and chat_session.company_id:
                company_id = chat_session.company_id
        else:
            # Create a new session
            title = chat_crud.generate_session_title(request.query)
            chat_session = chat_crud.create_session(
                session=session,
                tenant_id=user.tenant_id,
                user_id=user.id,
                title=title,
                company_id=company_id,
                document_ids=request.document_ids
            )

        # Get conversation history from session
        conversation_history = None
        if request.conversation_history:
            # Use provided history (for backward compatibility)
            conversation_history = [
                {"role": msg.role, "content": msg.content}
                for msg in request.conversation_history
            ]
        elif chat_session:
            # Get history from database
            conversation_history = chat_crud.get_conversation_history(
                session=session,
                session_id=chat_session.id,
                tenant_id=user.tenant_id
            )

        # Get document IDs from session if not provided in request
        doc_ids = request.document_ids
        if doc_ids is None and chat_session and chat_session.document_ids_json:
            doc_ids = json.loads(chat_session.document_ids_json)

        # Save user message
        chat_crud.add_message(
            session=session,
            session_id=chat_session.id,
            tenant_id=user.tenant_id,
            role=MessageRole.USER,
            content=request.query
        )

        result = rag_service.chat(
            session=session,
            query=request.query,
            tenant_id=user.tenant_id,
            company_id=company_id,
            document_ids=doc_ids,
            conversation_history=conversation_history,
            top_k=request.top_k or 5
        )

        # Get document names for sources (separate document and connector sources)
        doc_source_ids = list(set(
            s["document_id"] for s in result.get("sources", [])
            if s.get("source_type", "document") == "document"
        ))
        connector_source_ids = list(set(
            s["document_id"] for s in result.get("sources", [])
            if s.get("source_type") == "connector"
        ))

        doc_name_map = {}
        if doc_source_ids:
            docs = session.exec(
                select(Document).where(Document.id.in_(doc_source_ids))
            ).all()
            doc_name_map = {d.id: d.original_filename for d in docs}

        connector_name_map = {}
        if connector_source_ids:
            connectors = session.exec(
                select(ConnectorConfig).where(ConnectorConfig.id.in_(connector_source_ids))
            ).all()
            connector_name_map = {c.id: c.external_company_name or f"{c.connector_type.value} Connector" for c in connectors}

        # Format response
        sources = []
        for s in result.get("sources", []):
            source_type = s.get("source_type", "document")
            if source_type == "connector":
                source_name = connector_name_map.get(s["document_id"], "Unknown Connector")
                # For connector sources, include entity info in name
                entity_type = s.get("entity_type", "")
                entity_name = s.get("entity_name", "")
                if entity_name:
                    source_name = f"{source_name} - {entity_type}: {entity_name}"
                elif entity_type:
                    source_name = f"{source_name} - {entity_type}"
            else:
                source_name = doc_name_map.get(s["document_id"], "Unknown")

            sources.append(SourceInfo(
                chunk_id=s["chunk_id"],
                document_id=s["document_id"],
                document_name=source_name,
                page_number=s["page_number"],
                pillar=s["pillar"],
                pillar_label=get_pillar_label(s["pillar"]),
                similarity=s["similarity"],
                summary=s.get("summary", ""),
                source_type=source_type,
                connector_type=s.get("connector_type"),
                entity_type=s.get("entity_type"),
                entity_name=s.get("entity_name")
            ))

        chunks = [
            ChunkInfo(
                id=c["id"],
                document_id=c["document_id"],
                content=c["content"],
                summary=c.get("summary"),
                previous_context=c.get("previous_context"),
                pillar=c["pillar"],
                chunk_type=c["chunk_type"],
                page_number=c["page_number"],
                similarity=c.get("similarity", 0)
            )
            for c in result.get("chunks", [])
        ]

        # Save assistant message with sources
        sources_for_db = [s.model_dump() for s in sources]
        chat_crud.add_message(
            session=session,
            session_id=chat_session.id,
            tenant_id=user.tenant_id,
            role=MessageRole.ASSISTANT,
            content=result["answer"],
            sources=sources_for_db,
            usage_stats=result.get("usage_stats")
        )

        return ChatResponse(
            answer=result["answer"],
            sources=sources,
            chunks=chunks,
            usage_stats=result.get("usage_stats", {}),
            session_id=chat_session.id
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Chat] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




@router.post("/search", response_model=SearchResponse)
async def semantic_search(
    request: SearchRequest,
    user: User = Depends(require_permission(Permissions.FILES_READ)),
    session: Session = Depends(get_session),
):
    """
    Semantic search across document chunks.
    Returns relevant chunks without generating an answer.
    """
    logger.info(f"[Search] Query: {request.query[:100]}...")

    try:
        rag_service = get_rag_service()

        chunks = rag_service.search_similar_chunks(
            session=session,
            query=request.query,
            tenant_id=user.tenant_id,
            document_ids=request.document_ids,
            top_k=request.top_k or 10,
            similarity_threshold=request.similarity_threshold or 0.5
        )

        chunk_responses = [
            ChunkInfo(
                id=c["id"],
                document_id=c["document_id"],
                content=c["content"],
                summary=c.get("summary"),
                previous_context=c.get("previous_context"),
                pillar=c["pillar"],
                chunk_type=c["chunk_type"],
                page_number=c["page_number"],
                similarity=c.get("similarity", 0)
            )
            for c in chunks
        ]

        return SearchResponse(
            chunks=chunk_responses,
            total=len(chunk_responses)
        )

    except Exception as e:
        logger.error(f"[Search] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# WebSocket Endpoint for Streaming Chat
# =============================================================================

@router.websocket("/ws")
async def chat_websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time chat streaming.

    Client flow:
    1. Connect to WebSocket
    2. Send auth: {"type": "auth", "token": "..."}
    3. Send query: {"type": "query", "data": {...}}
    4. Receive status updates, sources, chunks, done

    Message types from server:
    - {"type": "status", "phase": "searching|generating", "message": "..."}
    - {"type": "session", "session_id": "..."}
    - {"type": "sources", "data": {...}}
    - {"type": "chunk", "data": "..."}
    - {"type": "done"}
    - {"type": "error", "message": "..."}
    """
    user_id = None
    user = None

    try:
        await websocket.accept()

        # Wait for auth message
        auth_data = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)

        if auth_data.get("type") != "auth":
            await websocket.send_json({"type": "error", "message": "Expected auth message"})
            await websocket.close(code=4001)
            return

        # Validate token from cookie or message
        token = auth_data.get("token")
        if not token:
            # Try to get from cookie
            cookies = websocket.cookies
            token = cookies.get("access_token")

        if not token:
            await websocket.send_json({"type": "error", "message": "No auth token provided"})
            await websocket.close(code=4001)
            return

        # Decode and validate token
        try:
            payload = decode_token(token)
            azure_oid = payload.get("oid") or payload.get("sub")
            azure_tid = payload.get("tid")

            if not azure_oid:
                raise ValueError("Invalid token payload")

            # Get user from database
            from sqlmodel import Session as SQLSession
            with SQLSession(engine) as db_session:
                user = get_user_by_azure_id(db_session, azure_oid, azure_tid)
                if not user:
                    raise ValueError("User not found")
                if not user.is_active:
                    raise ValueError("User account is deactivated")

                user_id = user.id
                tenant_id = user.tenant_id

        except Exception as e:
            logger.error(f"[ChatWS] Auth failed: {e}")
            await websocket.send_json({"type": "error", "message": "Authentication failed"})
            await websocket.close(code=4001)
            return

        # Register connection
        await chat_ws_manager.connect(websocket, user_id)
        await websocket.send_json({"type": "connected", "user_id": user_id})
        logger.info(f"[ChatWS] Connected for user: {user_id}")

        # Handle messages
        while True:
            try:
                message = await asyncio.wait_for(websocket.receive_json(), timeout=60.0)
                msg_type = message.get("type")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                    continue

                if msg_type == "pong":
                    continue

                if msg_type == "query":
                    # Process chat query
                    query_data = message.get("data", {})
                    await _process_ws_chat_query(
                        websocket=websocket,
                        user_id=user_id,
                        tenant_id=tenant_id,
                        query=query_data.get("query", ""),
                        session_id=query_data.get("session_id"),
                        company_id=query_data.get("company_id"),
                        document_ids=query_data.get("document_ids"),
                        top_k=query_data.get("top_k", 5)
                    )

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                try:
                    await websocket.send_json({"type": "ping"})
                except Exception:
                    break

    except WebSocketDisconnect:
        logger.info(f"[ChatWS] Client disconnected: {user_id}")
    except Exception as e:
        logger.error(f"[ChatWS] Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except Exception:
            pass
    finally:
        if user_id:
            await chat_ws_manager.disconnect(websocket, user_id)


async def _process_ws_chat_query(
    websocket: WebSocket,
    user_id: str,
    tenant_id: str,
    query: str,
    session_id: Optional[str] = None,
    company_id: Optional[str] = None,
    document_ids: Optional[List[str]] = None,
    top_k: int = 5
):
    """Process a chat query and stream results via WebSocket."""
    from sqlmodel import Session as SQLSession

    try:
        with SQLSession(engine) as session:
            rag_service = get_rag_service()

            # Get or create chat session
            chat_session = None
            if session_id:
                chat_session = chat_crud.get_session(
                    session=session,
                    session_id=session_id,
                    tenant_id=tenant_id
                )
                if not chat_session:
                    await websocket.send_json({"type": "error", "message": "Chat session not found"})
                    return
                if chat_session.user_id != user_id:
                    await websocket.send_json({"type": "error", "message": "Access denied"})
                    return
                if not company_id and chat_session.company_id:
                    company_id = chat_session.company_id
            else:
                title = chat_crud.generate_session_title(query)
                chat_session = chat_crud.create_session(
                    session=session,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    title=title,
                    company_id=company_id,
                    document_ids=document_ids
                )

            # Send session ID
            await websocket.send_json({"type": "session", "session_id": chat_session.id})

            # Get conversation history
            conversation_history = chat_crud.get_conversation_history(
                session=session,
                session_id=chat_session.id,
                tenant_id=tenant_id
            )

            # Get document IDs from session if not provided
            doc_ids = document_ids
            if doc_ids is None and chat_session and chat_session.document_ids_json:
                doc_ids = json.loads(chat_session.document_ids_json)

            # Save user message
            chat_crud.add_message(
                session=session,
                session_id=chat_session.id,
                tenant_id=tenant_id,
                role=MessageRole.USER,
                content=query
            )

            # Stream the response
            full_answer = ""
            sources_data = None

            for event in rag_service.chat_stream(
                session=session,
                query=query,
                tenant_id=tenant_id,
                company_id=company_id,
                document_ids=doc_ids,
                conversation_history=conversation_history,
                top_k=top_k
            ):
                if event["type"] == "status":
                    await websocket.send_json(event)

                elif event["type"] == "sources":
                    sources_data = event["data"]
                    # Get document names (separate document and connector sources)
                    doc_source_ids = list(set(
                        s["document_id"] for s in sources_data.get("sources", [])
                        if s.get("source_type", "document") == "document"
                    ))
                    connector_source_ids = list(set(
                        s["document_id"] for s in sources_data.get("sources", [])
                        if s.get("source_type") == "connector"
                    ))

                    doc_name_map = {}
                    if doc_source_ids:
                        docs = session.exec(
                            select(Document).where(Document.id.in_(doc_source_ids))
                        ).all()
                        doc_name_map = {d.id: d.original_filename for d in docs}

                    connector_name_map = {}
                    if connector_source_ids:
                        connectors = session.exec(
                            select(ConnectorConfig).where(ConnectorConfig.id.in_(connector_source_ids))
                        ).all()
                        connector_name_map = {c.id: c.external_company_name or f"{c.connector_type.value} Connector" for c in connectors}

                    # Enrich sources
                    enriched_sources = []
                    for s in sources_data.get("sources", []):
                        source_type = s.get("source_type", "document")
                        if source_type == "connector":
                            source_name = connector_name_map.get(s["document_id"], "Unknown Connector")
                            entity_type = s.get("entity_type", "")
                            entity_name = s.get("entity_name", "")
                            if entity_name:
                                source_name = f"{source_name} - {entity_type}: {entity_name}"
                            elif entity_type:
                                source_name = f"{source_name} - {entity_type}"
                        else:
                            source_name = doc_name_map.get(s["document_id"], "Unknown")

                        enriched_sources.append({
                            **s,
                            "document_name": source_name,
                            "pillar_label": get_pillar_label(s["pillar"]),
                            "source_type": source_type,
                            "connector_type": s.get("connector_type"),
                            "entity_type": s.get("entity_type"),
                            "entity_name": s.get("entity_name")
                        })
                    sources_data["sources"] = enriched_sources

                    await websocket.send_json({"type": "sources", "data": sources_data})

                elif event["type"] == "chunk":
                    full_answer += event["data"]
                    await websocket.send_json({"type": "chunk", "data": event["data"]})
                    # Small delay to force network flush - helps with Azure buffering
                    await asyncio.sleep(0.01)

                elif event["type"] == "done":
                    # Save assistant message
                    sources_for_db = sources_data.get("sources", []) if sources_data else []
                    chat_crud.add_message(
                        session=session,
                        session_id=chat_session.id,
                        tenant_id=tenant_id,
                        role=MessageRole.ASSISTANT,
                        content=full_answer,
                        sources=sources_for_db
                    )
                    await websocket.send_json({"type": "done"})

    except Exception as e:
        logger.error(f"[ChatWS] Query processing error: {e}")
        await websocket.send_json({"type": "error", "message": str(e)})

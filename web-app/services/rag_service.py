from typing import List, Optional, Dict, Any
from sqlmodel import Session, select, text

from database.models.document import DocumentChunk, Document
from database.models.connector import ConnectorChunk
from services.embedding_service import get_embedding_service
from services.llm_client import get_llm_client
from services.prompt_service import get_prompt_service
from utils.logger import get_logger

logger = get_logger(__name__)

# Default number of chunks to retrieve
DEFAULT_TOP_K = 5
# Default similarity threshold (lowered for better recall)
DEFAULT_SIMILARITY_THRESHOLD = 0.3

# Greeting patterns to skip RAG search
GREETING_PATTERNS = {
    "hi", "hello", "hey", "hii", "hiii", "hiiii",
    "good morning", "good afternoon", "good evening", "good night",
    "morning", "afternoon", "evening",
    "howdy", "greetings", "sup", "what's up", "whats up",
    "yo", "hola", "bonjour", "namaste",
    "how are you", "how r u", "how are u",
    "thanks", "thank you", "thx", "ty",
    "bye", "goodbye", "see you", "later",
    "nice to meet you", "pleased to meet you",
    "who are you", "what are you", "what can you do",
}


def is_greeting(query: str) -> bool:
    """Check if the query is a greeting or casual message."""
    normalized = query.lower().strip().rstrip("!?.,")
    # Exact match
    if normalized in GREETING_PATTERNS:
        return True
    # Check if starts with greeting and is short
    for greeting in GREETING_PATTERNS:
        if normalized.startswith(greeting) and len(normalized) < len(greeting) + 15:
            return True
    return False


class RAGService:
    """
    Retrieval-Augmented Generation service for document Q&A.
    Uses vector similarity search to find relevant chunks, then generates answers.
    Supports conversational context through query rewriting.
    """

    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.llm_client = get_llm_client()
        self.prompt_service = get_prompt_service()
        logger.info("[RAGService] Initialized")

    def rewrite_query_with_context(
        self,
        query: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """
        Rewrite a user query to be standalone by incorporating conversation context.

        This helps with follow-up questions like "What about its pricing?" by
        rewriting them to "What is the pricing for [Product X]?" based on context.

        Args:
            query: The user's current query
            conversation_history: List of previous messages with 'role' and 'content'

        Returns:
            A standalone query that can be used for retrieval
        """
        if not conversation_history:
            return query

        # Take last 6 messages for context
        recent_history = conversation_history[-6:]

        # Build conversation context string
        history_text = "\n".join([
            f"{msg['role'].upper()}: {msg['content']}"
            for msg in recent_history
        ])

        system_prompt = """You are a query rewriter. Your task is to rewrite the user's latest query to be a standalone question that includes all necessary context from the conversation.

Rules:
- If the query references something from the conversation (like "it", "that", "they", "this company", "the document", etc.), replace those references with the actual entities
- If the query is already standalone and clear, return it unchanged
- Keep the rewritten query concise and focused
- Do NOT add extra information not implied by the conversation
- Do NOT answer the question, just rewrite it
- Return ONLY the rewritten query, nothing else"""

        user_message = f"""Conversation history:
{history_text}

Latest query: {query}

Rewrite the latest query to be standalone:"""

        try:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ]

            response, usage_stats = self.llm_client.chat_completion(
                messages=messages,
                max_tokens=200,
                temperature=0.1
            )

            rewritten = response.strip()

            # If response is empty or excessively long, use original
            if not rewritten or len(rewritten) > 500:
                logger.info(f"[RAGService] Query rewrite returned invalid result, using original")
                return query

            logger.info(f"[RAGService] Query rewritten: '{query}' -> '{rewritten}'")
            return rewritten

        except Exception as e:
            logger.warning(f"[RAGService] Query rewrite failed: {e}, using original query")
            return query

    def search_similar_chunks(
        self,
        session: Session,
        query: str,
        tenant_id: str,
        company_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        top_k: int = DEFAULT_TOP_K,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
        include_connectors: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for chunks similar to the query using vector similarity.
        Searches both document chunks and connector chunks.

        Args:
            session: Database session
            query: User's search query
            tenant_id: Tenant ID for filtering
            company_id: Optional company ID for filtering
            document_ids: Optional list of document IDs to search within (only affects document chunks)
            top_k: Number of results to return
            similarity_threshold: Minimum similarity score (0-1)
            include_connectors: Whether to include connector chunks in search

        Returns:
            List of chunk dicts with similarity scores
        """
        if not self.embedding_service.is_configured():
            raise ValueError("Embedding service not configured")

        # Generate embedding for the query
        logger.info(f"[RAGService] Generating embedding for query: {query[:50]}...")
        logger.info(f"[RAGService] Search params - tenant_id: {tenant_id}, company_id: {company_id}, top_k: {top_k}, threshold: {similarity_threshold}")
        if document_ids:
            logger.info(f"[RAGService] Filtering by document_ids: {document_ids}")
        query_embedding = self.embedding_service.generate_embedding(query)

        # Build the similarity search query using pgvector
        # Using cosine similarity: 1 - (embedding <=> query_embedding)
        # Convert embedding list to string format for pgvector
        embedding_str = f"[{','.join(map(str, query_embedding))}]"

        connection = session.connection()
        all_chunks = []

        # =====================================================================
        # Search Document Chunks
        # =====================================================================
        doc_sql = f"""
            SELECT
                id,
                document_id,
                content,
                summary,
                previous_context,
                pillar,
                chunk_type,
                page_number,
                chunk_index,
                confidence_score,
                metadata_json,
                'document' as source_type,
                NULL as connector_type,
                NULL as entity_type,
                NULL as entity_name,
                1 - (embedding <=> '{embedding_str}'::vector) as similarity
            FROM document_chunks
            WHERE tenant_id = :tenant_id
            AND embedding IS NOT NULL
        """

        # Filter by company ID if provided
        if company_id:
            doc_sql += f" AND company_id = '{company_id}'"

        # Filter by document IDs if provided
        if document_ids:
            doc_ids_str = ",".join([f"'{d}'" for d in document_ids])
            doc_sql += f" AND document_id IN ({doc_ids_str})"

        # Add similarity threshold and ordering
        doc_sql += f"""
            AND 1 - (embedding <=> '{embedding_str}'::vector) >= {similarity_threshold}
            ORDER BY embedding <=> '{embedding_str}'::vector
            LIMIT {top_k}
        """

        result = connection.execute(text(doc_sql), {"tenant_id": tenant_id})

        for row in result:
            chunk_data = {
                "id": row.id,
                "document_id": row.document_id,
                "content": row.content,
                "summary": row.summary,
                "previous_context": row.previous_context,
                "pillar": row.pillar,
                "chunk_type": row.chunk_type,
                "page_number": row.page_number,
                "chunk_index": row.chunk_index,
                "confidence_score": row.confidence_score,
                "metadata_json": row.metadata_json,
                "source_type": "document",
                "connector_type": None,
                "entity_type": None,
                "entity_name": None,
                "similarity": row.similarity
            }
            all_chunks.append(chunk_data)
            logger.info(f"[RAGService] Doc chunk {row.chunk_index} (page {row.page_number}): similarity={row.similarity:.4f}, pillar={row.pillar}")

        # =====================================================================
        # Search Connector Chunks (if enabled)
        # =====================================================================
        if include_connectors:
            conn_sql = f"""
                SELECT
                    id,
                    connector_config_id as document_id,
                    content,
                    summary,
                    NULL as previous_context,
                    pillar,
                    chunk_type,
                    0 as page_number,
                    0 as chunk_index,
                    confidence_score,
                    metadata_json::text as metadata_json,
                    'connector' as source_type,
                    connector_type,
                    entity_type,
                    entity_name,
                    1 - (embedding <=> '{embedding_str}'::vector) as similarity
                FROM connector_chunks
                WHERE tenant_id = :tenant_id
                AND embedding IS NOT NULL
            """

            # Filter by company ID if provided
            if company_id:
                conn_sql += f" AND company_id = '{company_id}'"

            # Add similarity threshold and ordering
            conn_sql += f"""
                AND 1 - (embedding <=> '{embedding_str}'::vector) >= {similarity_threshold}
                ORDER BY embedding <=> '{embedding_str}'::vector
                LIMIT {top_k}
            """

            conn_result = connection.execute(text(conn_sql), {"tenant_id": tenant_id})

            for row in conn_result:
                chunk_data = {
                    "id": row.id,
                    "document_id": row.document_id,  # Actually connector_config_id
                    "content": row.content,
                    "summary": row.summary,
                    "previous_context": None,
                    "pillar": row.pillar,
                    "chunk_type": row.chunk_type,
                    "page_number": 0,
                    "chunk_index": 0,
                    "confidence_score": row.confidence_score,
                    "metadata_json": row.metadata_json,
                    "source_type": "connector",
                    "connector_type": row.connector_type,
                    "entity_type": row.entity_type,
                    "entity_name": row.entity_name,
                    "similarity": row.similarity
                }
                all_chunks.append(chunk_data)
                logger.info(f"[RAGService] Connector chunk ({row.entity_type}): similarity={row.similarity:.4f}, pillar={row.pillar}")

        # =====================================================================
        # Merge and re-rank by similarity
        # =====================================================================
        all_chunks.sort(key=lambda x: x["similarity"], reverse=True)
        all_chunks = all_chunks[:top_k]

        logger.info(f"[RAGService] Found {len(all_chunks)} similar chunks total (threshold: {similarity_threshold})")

        # Log stats
        doc_count = sum(1 for c in all_chunks if c["source_type"] == "document")
        conn_count = sum(1 for c in all_chunks if c["source_type"] == "connector")
        logger.info(f"[RAGService] Results: {doc_count} document chunks, {conn_count} connector chunks")

        return all_chunks

    def generate_answer(
        self,
        session: Session,
        query: str,
        chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        document_context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an answer based on retrieved chunks and conversation history.

        Args:
            session: Database session for fetching prompt
            query: User's question
            chunks: Retrieved relevant chunks
            conversation_history: Previous messages in the conversation
            document_context: Optional context about the document(s)

        Returns:
            Dict with 'answer', 'sources', 'usage_stats'
        """
        if not self.llm_client.is_configured():
            raise ValueError("LLM client not configured")

        # Build context from chunks
        context_parts = []
        sources = []

        for i, chunk in enumerate(chunks, 1):
            # Build chunk context with previous context for continuity
            pillar = chunk.get("pillar", "general")
            source_type = chunk.get("source_type", "document")

            # Different labeling for document vs connector chunks
            if source_type == "connector":
                entity_type = chunk.get("entity_type", "data")
                entity_name = chunk.get("entity_name", "")
                connector_type = chunk.get("connector_type", "connector")
                chunk_text = f"[Source {i}] (QuickBooks {entity_type}"
                if entity_name:
                    chunk_text += f": {entity_name}"
                chunk_text += f", Pillar: {pillar})"
            else:
                chunk_text = f"[Source {i}] (Document, Pillar: {pillar})"
                if chunk.get("previous_context"):
                    chunk_text += f"\nPrevious context: {chunk['previous_context']}"

            chunk_text += f"\nContent: {chunk['content']}"
            if chunk.get("summary"):
                chunk_text += f"\nSummary: {chunk['summary']}"

            context_parts.append(chunk_text)

            # Build source info
            source_info = {
                "chunk_id": chunk["id"],
                "document_id": chunk["document_id"],
                "page_number": chunk["page_number"],
                "pillar": chunk["pillar"],
                "similarity": chunk.get("similarity", 0),
                "summary": chunk.get("summary", ""),
                "source_type": source_type,
            }

            # Add connector-specific info
            if source_type == "connector":
                source_info["connector_type"] = chunk.get("connector_type")
                source_info["entity_type"] = chunk.get("entity_type")
                source_info["entity_name"] = chunk.get("entity_name")

            sources.append(source_info)

        context = "\n\n---\n\n".join(context_parts)

        # Get system prompt from database (with caching)
        system_prompt = self.prompt_service.get_rag_prompt(session)

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided (last 6 messages for context)
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)

        # Add current context and question
        user_message = f"""## Document Context:
{document_context if document_context else "No additional document context."}

## Retrieved Information:
{context}

## Question:
{query}

Please provide a comprehensive answer based on the above context."""

        messages.append({"role": "user", "content": user_message})

        # Generate response
        logger.info(f"[RAGService] Generating answer...")
        response, usage_stats = self.llm_client.chat_completion(
            messages=messages,
            max_tokens=2000,
            temperature=0.3
        )

        logger.info(f"[RAGService] Answer generated. Tokens: {usage_stats.get('total_tokens', 0)}")

        return {
            "answer": response,
            "sources": sources,
            "usage_stats": usage_stats
        }

    def generate_response_without_context(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        is_greeting: bool = False
    ) -> Dict[str, Any]:
        """
        Generate a response without document context (for greetings, casual chat, etc.)

        Args:
            query: User's message
            conversation_history: Previous messages in the conversation
            is_greeting: Whether the query is a greeting/casual message

        Returns:
            Dict with 'answer', 'sources', 'chunks', 'usage_stats'
        """
        if not self.llm_client.is_configured():
            raise ValueError("LLM client not configured")

        # If not a greeting, return a fixed "no information found" response
        if not is_greeting:
            logger.info(f"[RAGService] No relevant information found for query: {query[:50]}...")
            return {
                "answer": "I couldn't find any relevant information in the uploaded documents to answer your question. Please try rephrasing your question or ensure the relevant documents have been uploaded.",
                "sources": [],
                "chunks": [],
                "usage_stats": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            }

        # For greetings, let the LLM respond naturally
        system_prompt = """You are a helpful assistant for Business Due Diligence Evaluation (BDE).
You help users analyze documents and answer questions about business due diligence.

Guidelines:
- For greetings or casual conversation, respond in a friendly and professional manner
- Keep casual responses brief and offer to help with document analysis or questions
- If asked about yourself, explain that you're a BDE assistant that helps analyze business documents"""

        messages = [{"role": "system", "content": system_prompt}]

        # Add conversation history if provided (last 6 messages for context)
        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)

        messages.append({"role": "user", "content": query})

        logger.info(f"[RAGService] Generating response for greeting: {query[:50]}...")
        response, usage_stats = self.llm_client.chat_completion(
            messages=messages,
            max_tokens=500,
            temperature=0.7
        )

        return {
            "answer": response,
            "sources": [],
            "chunks": [],
            "usage_stats": usage_stats
        }

    def chat(
        self,
        session: Session,
        query: str,
        tenant_id: str,
        company_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = DEFAULT_TOP_K
    ) -> Dict[str, Any]:
        """
        Main chat method: retrieves relevant chunks and generates an answer.
        Handles greetings and casual conversation automatically when no chunks are found.
        Uses query rewriting for better retrieval on follow-up questions.

        Args:
            session: Database session
            query: User's question
            tenant_id: Tenant ID
            company_id: Optional company ID to filter by
            document_ids: Optional document IDs to search within
            conversation_history: Previous conversation messages (last 5-6 recommended)
            top_k: Number of chunks to retrieve

        Returns:
            Dict with 'answer', 'sources', 'chunks', 'usage_stats'
        """
        logger.info(f"[RAGService] Processing chat query: {query[:100]}...")

        # Check for greetings - skip embedding call entirely
        if is_greeting(query):
            logger.info(f"[RAGService] Greeting detected, skipping search")
            return self.generate_response_without_context(query, conversation_history, is_greeting=True)

        # Step 1: Rewrite query with conversation context for better retrieval
        search_query = query
        if conversation_history:
            search_query = self.rewrite_query_with_context(query, conversation_history)

        # Step 2: Retrieve relevant chunks using the rewritten query
        chunks = self.search_similar_chunks(
            session=session,
            query=search_query,
            tenant_id=tenant_id,
            company_id=company_id,
            document_ids=document_ids,
            top_k=top_k
        )

        # If no chunks found, return "no information found" response
        if not chunks:
            logger.info(f"[RAGService] No chunks found, returning no information found response")
            return self.generate_response_without_context(query, conversation_history, is_greeting=False)

        # Get document context if searching specific documents
        document_context = None
        if document_ids:
            docs = session.exec(
                select(Document).where(Document.id.in_(document_ids))
            ).all()
            if docs:
                doc_summaries = [f"- {d.original_filename}: {d.document_summary or 'No summary'}" for d in docs]
                document_context = "Documents being searched:\n" + "\n".join(doc_summaries)

        # Step 3: Generate answer with original query and conversation history
        # (use original query so the LLM sees what the user actually asked)
        result = self.generate_answer(
            session=session,
            query=query,
            chunks=chunks,
            conversation_history=conversation_history,
            document_context=document_context
        )

        result["chunks"] = chunks
        return result

    def chat_stream(
        self,
        session: Session,
        query: str,
        tenant_id: str,
        company_id: Optional[str] = None,
        document_ids: Optional[List[str]] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        top_k: int = DEFAULT_TOP_K
    ):
        """
        Streaming chat method: retrieves relevant chunks and streams the answer.

        Args:
            session: Database session
            query: User's question
            tenant_id: Tenant ID
            company_id: Optional company ID to filter by
            document_ids: Optional document IDs to search within
            conversation_history: Previous conversation messages
            top_k: Number of chunks to retrieve

        Yields:
            Dict events: {"type": "sources", "data": ...} then {"type": "chunk", "data": "..."}
        """
        logger.info(f"[RAGService] Processing streaming chat query: {query[:100]}...")

        # Check for greetings - handle without context
        if is_greeting(query):
            logger.info(f"[RAGService] Greeting detected, streaming without context")
            yield {"type": "status", "phase": "generating", "message": "Generating response..."}
            yield {"type": "sources", "data": {"sources": [], "chunks": []}}
            yield from self._stream_response_without_context(query, conversation_history, is_greeting=True)
            return

        # Step 1: Signal searching phase
        yield {"type": "status", "phase": "searching", "message": "Searching documents..."}

        # Rewrite query with conversation context
        search_query = query
        if conversation_history:
            search_query = self.rewrite_query_with_context(query, conversation_history)

        # Step 2: Retrieve relevant chunks
        chunks = self.search_similar_chunks(
            session=session,
            query=search_query,
            tenant_id=tenant_id,
            company_id=company_id,
            document_ids=document_ids,
            top_k=top_k
        )

        # If no chunks found, return "no information found" response
        if not chunks:
            logger.info(f"[RAGService] No chunks found, streaming no information found response")
            yield {"type": "status", "phase": "generating", "message": "Generating response..."}
            yield {"type": "sources", "data": {"sources": [], "chunks": []}}
            yield from self._stream_response_without_context(query, conversation_history, is_greeting=False)
            return

        # Build sources info
        sources = []
        for chunk in chunks:
            source_info = {
                "chunk_id": chunk["id"],
                "document_id": chunk["document_id"],
                "page_number": chunk["page_number"],
                "pillar": chunk["pillar"],
                "similarity": chunk.get("similarity", 0),
                "summary": chunk.get("summary", ""),
                "source_type": chunk.get("source_type", "document"),
            }
            # Add connector-specific info
            if chunk.get("source_type") == "connector":
                source_info["connector_type"] = chunk.get("connector_type")
                source_info["entity_type"] = chunk.get("entity_type")
                source_info["entity_name"] = chunk.get("entity_name")
            sources.append(source_info)

        # Step 3: Signal sources found and generating phase
        yield {"type": "status", "phase": "generating", "message": f"Found {len(sources)} relevant sections..."}
        yield {"type": "sources", "data": {"sources": sources, "chunks": chunks}}

        # Get document context
        document_context = None
        if document_ids:
            docs = session.exec(
                select(Document).where(Document.id.in_(document_ids))
            ).all()
            if docs:
                doc_summaries = [f"- {d.original_filename}: {d.document_summary or 'No summary'}" for d in docs]
                document_context = "Documents being searched:\n" + "\n".join(doc_summaries)

        # Step 4: Stream the answer
        yield from self._stream_answer(
            session=session,
            query=query,
            chunks=chunks,
            conversation_history=conversation_history,
            document_context=document_context
        )

    def _stream_answer(
        self,
        session: Session,
        query: str,
        chunks: List[Dict[str, Any]],
        conversation_history: Optional[List[Dict[str, str]]] = None,
        document_context: Optional[str] = None
    ):
        """Stream the answer generation."""
        # Build context from chunks
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            pillar = chunk.get("pillar", "general")
            chunk_text = f"[Source {i}] (Pillar: {pillar})"
            if chunk.get("previous_context"):
                chunk_text += f"\nPrevious context: {chunk['previous_context']}"
            chunk_text += f"\nContent: {chunk['content']}"
            if chunk.get("summary"):
                chunk_text += f"\nSummary: {chunk['summary']}"
            context_parts.append(chunk_text)

        context = "\n\n---\n\n".join(context_parts)

        # Get system prompt
        system_prompt = self.prompt_service.get_rag_prompt(session)

        # Build messages
        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)

        user_message = f"""## Document Context:
{document_context if document_context else "No additional document context."}

## Retrieved Information:
{context}

## Question:
{query}

Please provide a comprehensive answer based on the above context."""

        messages.append({"role": "user", "content": user_message})

        logger.info(f"[RAGService] Streaming answer generation...")
        for content_chunk in self.llm_client.chat_completion_stream(
            messages=messages,
            max_tokens=2000,
            temperature=0.3
        ):
            yield {"type": "chunk", "data": content_chunk}

        yield {"type": "done", "data": None}

    def _stream_response_without_context(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        is_greeting: bool = False
    ):
        """Stream a response without document context."""
        # If not a greeting, return a fixed "no information found" response
        if not is_greeting:
            logger.info(f"[RAGService] No relevant information found for query: {query[:50]}...")
            yield {"type": "chunk", "data": "I couldn't find any relevant information in the uploaded documents to answer your question. Please try rephrasing your question or ensure the relevant documents have been uploaded."}
            yield {"type": "done", "data": None}
            return

        # For greetings, let the LLM respond naturally
        system_prompt = """You are a helpful assistant for Business Due Diligence Evaluation (BDE).
You help users analyze documents and answer questions about business due diligence.

Guidelines:
- For greetings or casual conversation, respond in a friendly and professional manner
- Keep casual responses brief and offer to help with document analysis or questions
- If asked about yourself, explain that you're a BDE assistant that helps analyze business documents"""

        messages = [{"role": "system", "content": system_prompt}]

        if conversation_history:
            for msg in conversation_history[-6:]:
                messages.append(msg)

        messages.append({"role": "user", "content": query})

        logger.info(f"[RAGService] Streaming response for greeting: {query[:50]}...")
        for content_chunk in self.llm_client.chat_completion_stream(
            messages=messages,
            max_tokens=500,
            temperature=0.7
        ):
            yield {"type": "chunk", "data": content_chunk}

        yield {"type": "done", "data": None}


# Convenience function
def get_rag_service() -> RAGService:
    """Get a RAG service instance."""
    return RAGService()

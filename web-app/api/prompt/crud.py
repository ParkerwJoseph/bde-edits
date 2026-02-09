from datetime import datetime
from typing import Optional
from sqlmodel import Session, select

from database.models.prompt_template import PromptTemplate, DEFAULT_RAG_PROMPT
from api.prompt.schemas import PromptUpdate


def get_active_prompt(session: Session) -> Optional[PromptTemplate]:
    """Get the active RAG prompt template."""
    return session.exec(
        select(PromptTemplate).where(PromptTemplate.is_active == True)
    ).first()


def get_prompt_by_id(session: Session, prompt_id: str) -> Optional[PromptTemplate]:
    """Get prompt by ID."""
    return session.get(PromptTemplate, prompt_id)


def update_prompt(
    session: Session,
    prompt: PromptTemplate,
    data: PromptUpdate,
    updated_by: str
) -> PromptTemplate:
    """Update prompt template."""
    prompt.template = data.template
    prompt.version += 1
    prompt.updated_at = datetime.utcnow()
    prompt.updated_by = updated_by
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt


def reset_to_default(
    session: Session,
    prompt: PromptTemplate,
    updated_by: str
) -> PromptTemplate:
    """Reset prompt to default template."""
    prompt.template = DEFAULT_RAG_PROMPT
    prompt.version += 1
    prompt.updated_at = datetime.utcnow()
    prompt.updated_by = updated_by
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt


def create_default_prompt(session: Session) -> PromptTemplate:
    """Create the default RAG prompt if it doesn't exist."""
    prompt = PromptTemplate(
        name="RAG System Prompt",
        description="Main prompt for generating answers based on retrieved document chunks",
        template=DEFAULT_RAG_PROMPT,
        is_active=True,
        version=1
    )
    session.add(prompt)
    session.commit()
    session.refresh(prompt)
    return prompt

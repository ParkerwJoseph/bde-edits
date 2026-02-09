from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from database.connection import get_session
from database.models import User
from database.models.prompt_template import DEFAULT_RAG_PROMPT
from api.prompt import crud
from api.prompt.schemas import PromptUpdate, PromptResponse
from az_auth.dependencies import require_permission
from core.permissions import Permissions
from services.prompt_service import get_prompt_service

router = APIRouter()
prompt_service = get_prompt_service()


@router.get("", response_model=PromptResponse)
def get_prompt(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SETTINGS_READ)),
):
    """Get the active RAG prompt template."""
    prompt = crud.get_active_prompt(session)
    if not prompt:
        # Create default if doesn't exist
        prompt = crud.create_default_prompt(session)
    return prompt


@router.put("", response_model=PromptResponse)
def update_prompt(
    data: PromptUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SETTINGS_UPDATE)),
):
    """Update the RAG prompt template."""
    prompt = crud.get_active_prompt(session)
    if not prompt:
        prompt = crud.create_default_prompt(session)

    updated_by = current_user.email or current_user.display_name or str(current_user.id)
    result = crud.update_prompt(session, prompt, data, updated_by)
    prompt_service.invalidate_cache()
    return result


@router.post("/reset", response_model=PromptResponse)
def reset_prompt(
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.SETTINGS_UPDATE)),
):
    """Reset the RAG prompt to default template."""
    prompt = crud.get_active_prompt(session)
    if not prompt:
        prompt = crud.create_default_prompt(session)
        return prompt

    updated_by = current_user.email or current_user.display_name or str(current_user.id)
    result = crud.reset_to_default(session, prompt, updated_by)
    prompt_service.invalidate_cache()
    return result


@router.get("/default")
def get_default_prompt(
    current_user: User = Depends(require_permission(Permissions.SETTINGS_READ)),
):
    """Get the default RAG prompt template (for reference/comparison)."""
    return {"template": DEFAULT_RAG_PROMPT}

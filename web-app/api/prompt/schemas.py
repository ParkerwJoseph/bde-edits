from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PromptUpdate(BaseModel):
    template: str


class PromptResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    template: str
    is_active: bool
    version: int
    created_at: datetime
    updated_at: datetime
    updated_by: Optional[str]

    class Config:
        from_attributes = True

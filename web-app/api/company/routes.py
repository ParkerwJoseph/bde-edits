from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session

from database.connection import get_session
from database.models import User
from api.company import crud
from api.company.schemas import (
    CompanyCreate,
    CompanyUpdate,
    CompanyResponse,
    CompanyListResponse,
)
from az_auth.dependencies import require_permission
from core.permissions import Permissions

router = APIRouter()


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
def create_company(
    data: CompanyCreate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.FILES_UPLOAD)),
):
    """Create a new company for the current tenant."""
    # Check if company with same name already exists
    existing = crud.get_company_by_name(session, current_user.tenant_id, data.name)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="A company with this name already exists"
        )

    company = crud.create_company(session, current_user.tenant_id, data)
    return company


@router.get("", response_model=CompanyListResponse)
def list_companies(
    skip: int = 0,
    limit: int = 100,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.FILES_READ)),
):
    """List all companies for the current tenant."""
    companies = crud.get_companies_by_tenant(session, current_user.tenant_id, skip, limit)
    total = crud.get_companies_count(session, current_user.tenant_id)
    return CompanyListResponse(companies=companies, total=total)


@router.get("/{company_id}", response_model=CompanyResponse)
def get_company(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.FILES_READ)),
):
    """Get company details."""
    company = crud.get_company(session, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Ensure company belongs to user's tenant
    if company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return company


@router.patch("/{company_id}", response_model=CompanyResponse)
def update_company(
    company_id: str,
    data: CompanyUpdate,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.FILES_UPLOAD)),
):
    """Update company details."""
    company = crud.get_company(session, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Ensure company belongs to user's tenant
    if company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Check if new name conflicts with existing company
    if data.name and data.name != company.name:
        existing = crud.get_company_by_name(session, current_user.tenant_id, data.name)
        if existing:
            raise HTTPException(
                status_code=400,
                detail="A company with this name already exists"
            )

    return crud.update_company(session, company, data)


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_company(
    company_id: str,
    session: Session = Depends(get_session),
    current_user: User = Depends(require_permission(Permissions.FILES_DELETE)),
):
    """Delete a company and all associated data (documents, connectors, scores, etc.)."""
    company = crud.get_company(session, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    # Ensure company belongs to user's tenant
    if company.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    crud.delete_company(session, company)

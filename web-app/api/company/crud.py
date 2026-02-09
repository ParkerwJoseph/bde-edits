from datetime import datetime
from typing import Optional
from sqlmodel import Session, select, func
from sqlalchemy import delete

from database.models.company import Company
from database.models.document import Document, DocumentChunk
from database.models.chat import ChatSession, ChatMessageModel
from database.models.connector import (
    ConnectorConfig,
    ConnectorSyncLog,
    ConnectorRawData,
    ConnectorChunk,
)
from database.models.scoring import (
    CompanyMetric,
    PillarEvaluationCriteria,
    CompanyPillarScore,
    CompanyBDEScore,
    AcquisitionRecommendation,
    CompanyFlag,
)
from api.company.schemas import CompanyCreate, CompanyUpdate


def create_company(session: Session, tenant_id: str, data: CompanyCreate) -> Company:
    """Create a new company for a tenant."""
    company = Company(
        tenant_id=tenant_id,
        name=data.name,
    )
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def get_company(session: Session, company_id: str) -> Optional[Company]:
    """Get company by ID."""
    return session.get(Company, company_id)


def get_company_by_name(session: Session, tenant_id: str, name: str) -> Optional[Company]:
    """Get company by name within a tenant."""
    return session.exec(
        select(Company).where(
            Company.tenant_id == tenant_id,
            Company.name == name
        )
    ).first()


def get_companies_by_tenant(
    session: Session,
    tenant_id: str,
    skip: int = 0,
    limit: int = 100
) -> list[Company]:
    """Get all companies for a tenant with pagination."""
    return list(session.exec(
        select(Company)
        .where(Company.tenant_id == tenant_id)
        .order_by(Company.name)
        .offset(skip)
        .limit(limit)
    ).all())


def get_companies_count(session: Session, tenant_id: str) -> int:
    """Get total count of companies for a tenant."""
    result = session.exec(
        select(func.count(Company.id)).where(Company.tenant_id == tenant_id)
    ).one()
    return result


def update_company(session: Session, company: Company, data: CompanyUpdate) -> Company:
    """Update company details."""
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(company, key, value)
    company.updated_at = datetime.utcnow()
    session.add(company)
    session.commit()
    session.refresh(company)
    return company


def delete_company(session: Session, company: Company) -> None:
    """Delete a company and all associated data (cascade delete)."""
    company_id = company.id

    # Delete scoring-related data
    session.execute(delete(CompanyFlag).where(CompanyFlag.company_id == company_id))
    session.execute(delete(AcquisitionRecommendation).where(AcquisitionRecommendation.company_id == company_id))
    session.execute(delete(CompanyBDEScore).where(CompanyBDEScore.company_id == company_id))
    session.execute(delete(CompanyPillarScore).where(CompanyPillarScore.company_id == company_id))
    session.execute(delete(PillarEvaluationCriteria).where(PillarEvaluationCriteria.company_id == company_id))
    session.execute(delete(CompanyMetric).where(CompanyMetric.company_id == company_id))

    # Delete connector-related data
    session.execute(delete(ConnectorChunk).where(ConnectorChunk.company_id == company_id))
    session.execute(delete(ConnectorRawData).where(ConnectorRawData.company_id == company_id))
    session.execute(delete(ConnectorSyncLog).where(ConnectorSyncLog.company_id == company_id))
    session.execute(delete(ConnectorConfig).where(ConnectorConfig.company_id == company_id))

    # Delete chat messages first (they reference chat_sessions), then chat sessions
    # Get session IDs for this company first
    chat_session_ids = list(session.exec(
        select(ChatSession.id).where(ChatSession.company_id == company_id)
    ).all())
    if chat_session_ids:
        session.execute(delete(ChatMessageModel).where(ChatMessageModel.session_id.in_(chat_session_ids)))
    session.execute(delete(ChatSession).where(ChatSession.company_id == company_id))

    # Delete document chunks first, then documents
    session.execute(delete(DocumentChunk).where(DocumentChunk.company_id == company_id))
    session.execute(delete(Document).where(Document.company_id == company_id))

    # Finally, delete the company itself
    session.execute(delete(Company).where(Company.id == company_id))
    session.commit()
